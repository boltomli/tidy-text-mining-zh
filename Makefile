all: pdf epub html

pdf: index.Rmd
	Rscript -e 'bookdown::render_book("index.Rmd", output_format = "bookdown::pdf_book")'

epub: index.Rmd
	Rscript -e 'bookdown::render_book("index.Rmd", output_format = "bookdown::epub_book")'

html: index.Rmd
	Rscript -e 'bookdown::render_book("index.Rmd", output_format = "bookdown::gitbook")'

deploy:
	netlify deploy --prod

.PHONY: clean
clean:
	rm -rf _book _bookdown_files