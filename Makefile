.PHONY: all build install uninstall clean

all: build

build:
	python3 -m build

install:
	pip install . --force-reinstall
	@echo "Done! How to use \`conoha-dns -h\`"

uninstall:
	pip uninstall conoha-dns-cli -y

clean:
	rm -rf build dist *.egg-info