all:
	pdflatex -shell-escape -output-directory build/ main.tex
	cp build/main.pdf .

clean:
	rm -f build/*.aux  || true
	rm build/*/*.aux  || true
	rm build/main.*  || true
	rm build/*.log  || true
	rm -r build/_minted*  || true

bibliografia:
	biber  build/main	

