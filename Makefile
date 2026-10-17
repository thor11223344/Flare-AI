.PHONY: install install-ibmz pipeline app run test clean benchmark-ibmz
install:
	pip install -r requirements.txt
install-ibmz:
	python3 -m pip install --break-system-packages -r requirements-ibmz.txt
	sudo ln -sf /home/linux1/.local/lib/python3.12/site-packages/snapml /usr/local/lib/python3.12/dist-packages/snapml
pipeline:
	python run_all.py --no-app
app:
	streamlit run app/streamlit_app.py
run:
	python run_all.py
test:
	pytest -q
benchmark-ibmz:
	python3 src/ibmz/snapml_benchmark.py
clean:
	rm -rf data/*.db data/*.csv data/*.json data/*.png data/governance_logs

