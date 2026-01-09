.PHONY: install build test clean

install:
	pip install -e .

build-rust:
	cd rust-core && cargo build --release

build: build-rust install

test:
	pytest tests/

clean:
	cargo clean
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
