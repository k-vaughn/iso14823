.PHONY: data pages check serve

data:
	python3 scripts/import_annex.py

pages: data
	python3 scripts/build_pages.py

check:
	python3 -m unittest discover -s tests -v
	python3 scripts/import_annex.py --check
	python3 scripts/build_pages.py --check

serve: pages
	zensical serve
