// LazyOpt Server — Go stdlib only, zero external dependencies.
//
// Modes:
//   server.exe <file.html> [port]       — serve a single HTML file
//   server.exe file_sharing [port]      — serve current directory (file browser)
//   server.exe tunnel [port]            — encrypted TCP tunnel (AES-256-GCM)
//   server.exe [port]                   — file_sharing on given port (default 8080)
//
// Examples:
//   server.exe index.html
//   server.exe index.html 9000
//   server.exe file_sharing
//   server.exe file_sharing 9000
//   server.exe tunnel 5555

package main

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/ecdh"
	"crypto/rand"
	"crypto/sha256"
	"encoding/binary"
	"fmt"
	"io"
	"mime"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// ── HKDF / HMAC (stdlib only, no x/crypto) ───────────────────────────────────

func hmacSHA256(key, data []byte) []byte {
	const blockSize = 64
	if len(key) > blockSize {
		h := sha256.Sum256(key)
		key = h[:]
	}
	ipad := make([]byte, blockSize+len(data))
	opad := make([]byte, blockSize+sha256.Size)
	for i := 0; i < blockSize; i++ {
		k := byte(0)
		if i < len(key) {
			k = key[i]
		}
		ipad[i] = k ^ 0x36
		opad[i] = k ^ 0x5c
	}
	copy(ipad[blockSize:], data)
	inner := sha256.Sum256(ipad)
	copy(opad[blockSize:], inner[:])
	outer := sha256.Sum256(opad)
	return outer[:]
}

func deriveKey(secret []byte) []byte {
	salt := make([]byte, sha256.Size)
	prk := hmacSHA256(salt, secret)
	t := hmacSHA256(prk, append([]byte("encrypted-tunnel-v1"), 0x01))
	return t[:32]
}

// ── Tunnel: framed I/O ────────────────────────────────────────────────────────

func sendFrame(conn net.Conn, data []byte) error {
	hdr := make([]byte, 4)
	binary.BigEndian.PutUint32(hdr, uint32(len(data)))
	if _, err := conn.Write(hdr); err != nil {
		return err
	}
	_, err := conn.Write(data)
	return err
}

func recvFrame(conn net.Conn) ([]byte, error) {
	hdr := make([]byte, 4)
	if _, err := io.ReadFull(conn, hdr); err != nil {
		return nil, err
	}
	n := binary.BigEndian.Uint32(hdr)
	if n > 1<<20 {
		return nil, fmt.Errorf("frame too large: %d", n)
	}
	buf := make([]byte, n)
	_, err := io.ReadFull(conn, buf)
	return buf, err
}

func tunnelHandshake(conn net.Conn) ([]byte, error) {
	priv, err := ecdh.X25519().GenerateKey(rand.Reader)
	if err != nil {
		return nil, err
	}
	theirPubBytes := make([]byte, 32)
	if _, err := io.ReadFull(conn, theirPubBytes); err != nil {
		return nil, fmt.Errorf("recv pubkey: %w", err)
	}
	if _, err := conn.Write(priv.PublicKey().Bytes()); err != nil {
		return nil, fmt.Errorf("send pubkey: %w", err)
	}
	theirPub, err := ecdh.X25519().NewPublicKey(theirPubBytes)
	if err != nil {
		return nil, fmt.Errorf("bad client pubkey: %w", err)
	}
	shared, err := priv.ECDH(theirPub)
	if err != nil {
		return nil, err
	}
	return deriveKey(shared), nil
}

func tunnelEncrypt(gcm cipher.AEAD, plain []byte) ([]byte, error) {
	nonce := make([]byte, gcm.NonceSize())
	if _, err := rand.Read(nonce); err != nil {
		return nil, err
	}
	return append(nonce, gcm.Seal(nil, nonce, plain, nil)...), nil
}

func tunnelDecrypt(gcm cipher.AEAD, data []byte) ([]byte, error) {
	ns := gcm.NonceSize()
	if len(data) < ns {
		return nil, fmt.Errorf("frame too short")
	}
	return gcm.Open(nil, data[:ns], data[ns:], nil)
}

func handleTunnelConn(conn net.Conn) {
	defer conn.Close()
	addr := conn.RemoteAddr().String()
	fmt.Fprintf(os.Stderr, "[+] %s connected\n", addr)

	key, err := tunnelHandshake(conn)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[-] %s handshake failed: %v\n", addr, err)
		return
	}
	fmt.Fprintf(os.Stderr, "[*] %s tunnel up (AES-256-GCM)\n", addr)

	block, _ := aes.NewCipher(key)
	gcm, _ := cipher.NewGCM(block)
	done := make(chan struct{})

	go func() {
		defer close(done)
		for {
			frame, err := recvFrame(conn)
			if err != nil {
				fmt.Fprintf(os.Stderr, "[-] %s recv: %v\n", addr, err)
				return
			}
			plain, err := tunnelDecrypt(gcm, frame)
			if err != nil {
				fmt.Fprintf(os.Stderr, "[!] %s decrypt error: %v\n", addr, err)
				continue
			}
			os.Stdout.Write(plain)
		}
	}()

	buf := make([]byte, 65536)
	for {
		n, err := os.Stdin.Read(buf)
		if n > 0 {
			enc, _ := tunnelEncrypt(gcm, buf[:n])
			if sendFrame(conn, enc) != nil {
				break
			}
		}
		if err != nil {
			break
		}
	}
	<-done
	fmt.Fprintf(os.Stderr, "[-] %s disconnected\n", addr)
}

func runTunnel(port string) {
	ln, err := net.Listen("tcp", "0.0.0.0:"+port)
	if err != nil {
		fmt.Fprintln(os.Stderr, "listen:", err)
		os.Exit(1)
	}
	fmt.Fprintf(os.Stderr, "[tunnel] listening on 0.0.0.0:%s\n", port)
	for {
		conn, err := ln.Accept()
		if err != nil {
			fmt.Fprintln(os.Stderr, "accept:", err)
			continue
		}
		go handleTunnelConn(conn)
	}
}

// ── HTTP: single file ─────────────────────────────────────────────────────────

func runSingleFile(path, port string) {
	abs, err := filepath.Abs(path)
	if err != nil {
		fmt.Fprintln(os.Stderr, "bad path:", err)
		os.Exit(1)
	}
	ext := strings.ToLower(filepath.Ext(abs))
	mimeType := mime.TypeByExtension(ext)
	if mimeType == "" {
		mimeType = "application/octet-stream"
	}

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(os.Stderr, "[http] %s %s %s\n", r.RemoteAddr, r.Method, r.URL.Path)
		w.Header().Set("Content-Type", mimeType)
		http.ServeFile(w, r, abs)
	})

	fmt.Fprintf(os.Stderr, "[http] serving %s on http://0.0.0.0:%s\n", abs, port)
	if err := http.ListenAndServe("0.0.0.0:"+port, nil); err != nil {
		fmt.Fprintln(os.Stderr, "server error:", err)
		os.Exit(1)
	}
}

// ── HTTP: file browser (directory listing + download) ────────────────────────

func runFileSharing(port string) {
	cwd, _ := os.Getwd()

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(os.Stderr, "[http] %s %s %s\n", r.RemoteAddr, r.Method, r.URL.Path)

		// strip leading slash, resolve to real path
		rel := filepath.FromSlash(strings.TrimPrefix(r.URL.Path, "/"))
		abs := filepath.Join(cwd, rel)

		// security: don't escape cwd
		if !strings.HasPrefix(abs, cwd) {
			http.Error(w, "forbidden", 403)
			return
		}

		info, err := os.Stat(abs)
		if err != nil {
			http.Error(w, "not found", 404)
			return
		}

		if info.IsDir() {
			entries, err := os.ReadDir(abs)
			if err != nil {
				http.Error(w, "read dir error", 500)
				return
			}
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			fmt.Fprintf(w, `<!DOCTYPE html><html><head><meta charset="utf-8">
<title>LazyOpt File Sharing</title>
<style>
  body{font-family:monospace;background:#0d0d0d;color:#ccc;padding:2rem}
  h2{color:#4af}
  a{color:#7df;text-decoration:none}
  a:hover{text-decoration:underline}
  .entry{padding:4px 0;border-bottom:1px solid #222}
  .size{color:#888;float:right}
</style></head><body>
<h2>[DIR] %s</h2>`, r.URL.Path)
			if r.URL.Path != "/" {
				parent := filepath.ToSlash(filepath.Dir(strings.TrimSuffix(r.URL.Path, "/")))
				if parent == "" {
					parent = "/"
				}
				fmt.Fprintf(w, `<div class="entry"><a href="%s">[..] up</a></div>`, parent)
			}
			for _, e := range entries {
				name := e.Name()
				link := strings.TrimSuffix(r.URL.Path, "/") + "/" + name
				icon := "[F]"
				sizeStr := ""
				if e.IsDir() {
					icon = "[D]"
					name += "/"
				} else {
					if fi, err := e.Info(); err == nil {
						sizeStr = formatSize(fi.Size())
					}
				}
				fmt.Fprintf(w, `<div class="entry"><a href="%s">%s %s</a><span class="size">%s</span></div>`,
					link, icon, name, sizeStr)
			}
			fmt.Fprintf(w, `<br><small style="color:#555">LazyOpt file_sharing — %s</small></body></html>`,
				time.Now().Format("2006-01-02 15:04:05"))
			return
		}

		// serve file with download header
		w.Header().Set("Content-Disposition", "attachment; filename=\""+info.Name()+"\"")
		http.ServeFile(w, r, abs)
	})

	fmt.Fprintf(os.Stderr, "[file_sharing] serving %s on http://0.0.0.0:%s\n", cwd, port)
	if err := http.ListenAndServe("0.0.0.0:"+port, nil); err != nil {
		fmt.Fprintln(os.Stderr, "server error:", err)
		os.Exit(1)
	}
}

func formatSize(b int64) string {
	const unit = 1024
	if b < unit {
		return fmt.Sprintf("%d B", b)
	}
	div, exp := int64(unit), 0
	for n := b / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(b)/float64(div), "KMGTPE"[exp])
}

// ── Main ──────────────────────────────────────────────────────────────────────

func usage() {
	fmt.Fprintln(os.Stderr, `LazyOpt Server — usage:
  server <file.html> [port]       serve a single file (default port 8080)
  server file_sharing [port]      browse & download files in current dir
  server tunnel [port]            encrypted AES-256-GCM TCP tunnel (default 5555)
  server [port]                   same as file_sharing on given port`)
	os.Exit(1)
}

func isPort(s string) bool {
	n, err := strconv.Atoi(s)
	return err == nil && n > 0 && n < 65536
}

func main() {
	args := os.Args[1:]

	if len(args) == 0 {
		runFileSharing("8080")
		return
	}

	switch args[0] {
	case "file_sharing":
		port := "8080"
		if len(args) > 1 && isPort(args[1]) {
			port = args[1]
		}
		runFileSharing(port)

	case "tunnel":
		port := "5555"
		if len(args) > 1 && isPort(args[1]) {
			port = args[1]
		}
		runTunnel(port)

	default:
		// could be a port number or a filename
		if isPort(args[0]) {
			runFileSharing(args[0])
			return
		}
		// treat as filename
		path := args[0]
		if _, err := os.Stat(path); err != nil {
			fmt.Fprintf(os.Stderr, "file not found: %s\n", path)
			usage()
		}
		port := "8080"
		if len(args) > 1 && isPort(args[1]) {
			port = args[1]
		}
		runSingleFile(path, port)
	}
}
