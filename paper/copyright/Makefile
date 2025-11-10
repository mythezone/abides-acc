# Makefile for building software copyright application PDFs
# Location: paper/copyright
# Usage:
#   cd paper/copyright && make           # build main.pdf and code.pdf
#   cd paper/copyright && make clean     # remove aux files
#   cd paper/copyright && make distclean # remove aux + PDFs
#
# This Makefile tries the following compilers in order:
#   1) latexmk + xelatex
#   2) tectonic
#   3) docker (texlive/texlive image + xelatex)
#
# tikz-uml.sty and figures are referenced via \input@path in main.tex.

SHELL := /bin/bash
TEXFLAGS := -interaction=nonstopmode -halt-on-error -file-line-error
TECTONIC_FLAGS := -X compile --keep-logs --keep-intermediates --chatter=minimal

.PHONY: all clean distclean main code

all: main.pdf code.pdf

main: main.pdf
code: code.pdf

main.pdf: main.tex mancls.cls
	@set -e; \
	if command -v latexmk >/dev/null 2>&1 && command -v xelatex >/dev/null 2>&1; then \
		echo "[build] latexmk + xelatex -> main.pdf"; \
		latexmk -xelatex $(TEXFLAGS) main.tex; \
	elif command -v tectonic >/dev/null 2>&1; then \
		echo "[build] tectonic -> main.pdf"; \
		tectonic $(TECTONIC_FLAGS) main.tex || tectonic main.tex; \
	elif command -v docker >/dev/null 2>&1; then \
		echo "[build] docker(texlive) + xelatex -> main.pdf"; \
		docker run --rm -v "$$PWD":/project -w /project texlive/texlive:latest sh -lc \
			"xelatex $(TEXFLAGS) main.tex && xelatex $(TEXFLAGS) main.tex"; \
	else \
		echo "No LaTeX toolchain found. Please install TeX Live (xelatex + latexmk) or Tectonic, or use Docker."; \
		exit 1; \
	fi

code.pdf: code.tex mancls.cls
	@set -e; \
	if command -v latexmk >/dev/null 2>&1 && command -v xelatex >/dev/null 2>&1; then \
		echo "[build] latexmk + xelatex -> code.pdf"; \
		latexmk -xelatex $(TEXFLAGS) code.tex; \
	elif command -v tectonic >/dev/null 2>&1; then \
		echo "[build] tectonic -> code.pdf"; \
		tectonic $(TECTONIC_FLAGS) code.tex || tectonic code.tex; \
	elif command -v docker >/dev/null 2>&1; then \
		echo "[build] docker(texlive) + xelatex -> code.pdf"; \
		docker run --rm -v "$$PWD":/project -w /project texlive/texlive:latest sh -lc \
			"xelatex $(TEXFLAGS) code.tex && xelatex $(TEXFLAGS) code.tex"; \
	else \
		echo "No LaTeX toolchain found. Please install TeX Live (xelatex + latexmk) or Tectonic, or use Docker."; \
		exit 1; \
	fi

clean:
	@rm -f *.aux *.log *.out *.toc *.fls *.fdb_latexmk *.xdv *.synctex.gz

distclean: clean
	@rm -f main.pdf code.pdf
