python -m py_compile main.py && \
    docker build --platform linux/amd64 -t 192.168.1.2:9500/humid-server . && \
    docker push 192.168.1.2:9500/humid-server
