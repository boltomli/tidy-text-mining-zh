# Text Mining with R: A Tidy Approach

This is a fork, by Song Li, of the repo to note a few things down and modify the book [**Text Mining with R: A Tidy Approach**](http://tidytextmining.com/), by Julia Silge and David Robinson.

Please note that this work is written under a [Contributor Code of Conduct](CONDUCT.md) and released under a [CC-BY-NC-SA license](https://creativecommons.org/licenses/by-nc-sa/3.0/us/). By participating in this project (for example, by submitting a [pull request](https://github.com/boltomli/tidy-text-mining-zh/issues) with suggestions or edits) you agree to abide by its terms.

## Build

Dependency to build non-HTML format: `Rscript -e 'webshot::install_phantomjs()'`.

Run `make` to build all formats of the book, or `make html` `make pdf` `make epub` separately. Run `make deploy` to deploy to live site.
