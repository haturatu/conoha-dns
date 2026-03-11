.PHONY: all build test install uninstall clean

all: build

build:
	python3 -m build

test:
	PYTHONPATH=src python3 -m conoha_dns_cli.main --help > /dev/null

install:
	pip install . --force-reinstall
	@echo "Done! How to use \`conoha-dns -h\`"

uninstall:
	pip uninstall conoha-dns-cli -y

clean:
	rm -rf build dist *.egg-info
