########################################################################
# Phase 1 - Build Binaries
########################################################################
FROM alpine:latest AS builder

# Install build dependencies, Mosquitto, and its development libraries
RUN apk add --no-cache \
    build-base \
    mosquitto-dev \
    && rm -rf /var/cache/apk/*

WORKDIR /build
COPY logger.c /build/

# Easier than making the makefile conditional
RUN gcc -o logger logger.c -lmosquitto

########################################################################
# Phase 2 - Repack into runtime container
########################################################################
FROM alpine:latest

# Get the runtime version of the mosquitto libs
RUN apk add --no-cache \
    mosquitto-libs \
    && rm -rf /var/cache/apk/*

# Install the logger
COPY --from=builder /build/logger /usr/local/bin/

# Mount persistent data storage here
VOLUME /data

# Run the logger in the /data directory
WORKDIR /data
CMD ["/usr/local/bin/logger"]

