.PHONY: install pipeline app run test clean
install:
	pip install -r requirements.txt
pipeline:
	python run_all.py --no-app
app:
	streamlit run app/streamlit_app.py
run:
	python run_all.py
test:
	pytest -q
clean:
	rm -rf data/*.db data/*.csv data/*.json data/*.png data/governance_logs
