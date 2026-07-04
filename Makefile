all: pdf epub html

html:
	quarto render --to html

pdf:
	quarto render --to pdf

epub:
	quarto render --to epub

deploy:
	netlify deploy --prod

.PHONY: clean
clean:
	rm -rf _book
