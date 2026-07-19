.PHONY: all build test install uninstall clean

all: build

build:
	go build ./...

test:
	go test ./...

install:
	install -d "$(HOME)/.local/bin"
	go build -o "$(HOME)/.local/bin/conoha-dns" ./cmd/conoha-dns
	@echo "Done! How to use \`conoha-dns -h\`"

uninstall:
	rm -f "$(HOME)/.local/bin/conoha-dns"

clean:
	go clean ./...
