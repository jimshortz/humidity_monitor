FROM alpine:latest AS builder

# Set environment variables for Mosquitto and build dependencies
ENV MOSQUITTO_VERSION 2.0.15
ENV CFLAGS="-I/usr/local/include"
ENV LDFLAGS="-L/usr/local/lib"

# Install build dependencies, Mosquitto, and its development libraries
RUN apk add --no-cache \
    build-base \
    mosquitto-dev \
    && rm -rf /var/cache/apk/*

# Set the working directory in the container
WORKDIR /build

COPY Makefile logger.c .

RUN gcc -o logger logger.c -lmosquitto

FROM alpine:latest
RUN apk add --no-cache \
    mosquitto-libs \
    && rm -rf /var/cache/apk/*
    
COPY --from=builder /build/logger /usr/local/bin
VOLUME /data
WORKDIR /data
CMD ["/usr/local/bin/logger"]

