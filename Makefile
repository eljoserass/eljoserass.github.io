# make serve  -> preview at http://127.0.0.1:1111 (re-run after editing notes)
# make build  -> site in ./public
ZOLA ?= zola

build:
	python3 scripts/prepare.py . .build
	$(ZOLA) --root .build build --output-dir public --force

serve:
	python3 scripts/prepare.py . .build
	$(ZOLA) --root .build serve

.PHONY: build serve
