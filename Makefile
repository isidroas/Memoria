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

update-code:
	cd apendices; ./copy_quadrotor.py;
	cd apendices; ./copy_rpi_vision_uav.py
