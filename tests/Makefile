PYTHON=../env/bin/python3.5

default: check

$(PYTHON):
	virtualenv ../env -p /usr/bin/python3.5
	../env/bin/pip install -r ../requirements.txt

check: $(PYTHON)
	$(PYTHON) test_fetch.py
