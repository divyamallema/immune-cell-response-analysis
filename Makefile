PYTHON ?= python3
PORT ?= 8501

.PHONY: setup pipeline dashboard clean

setup:
	$(PYTHON) -m pip install -r requirements.txt

pipeline:
	$(PYTHON) load_data.py
	$(PYTHON) frequencies.py
	$(PYTHON) response_analysis.py
	$(PYTHON) subset_analysis.py

dashboard:
	$(PYTHON) -m streamlit run dashboard.py --server.port $(PORT) --server.address 0.0.0.0 --server.headless true

clean:
	rm -rf cell_counts.db outputs __pycache__
