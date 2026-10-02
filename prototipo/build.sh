#!/bin/sh
# Gera index.html standalone (com doctype/head) a partir de app.html, que é o corpo publicado como Artifact.
cd "$(dirname "$0")"
{ printf '<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head>\n<body>\n'; cat app.html; printf '\n</body>\n</html>\n'; } > index.html
