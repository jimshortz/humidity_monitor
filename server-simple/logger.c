#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <mosquitto.h>

static int run = 1;
static FILE* log_fh = NULL;

const char * mqtt_host;
int mqtt_port;
const char* mqtt_topic;

const char* getenv2(const char* name, const char* def) {
    const char* val;
    val = getenv(name);
    if (val != NULL)
	return val;
    return def;
}

void handle_signal(int s) {
    fprintf(stderr, "Aborting on signal %d\n", s);
    run = 0;
}

void connect_callback(struct mosquitto *mosq, void *obj, int result) {
    fprintf(stderr, "Connected (status %d)\n", result);
    if (result == 0) {
	fprintf(stderr, "Subscribing to topic %s\n", mqtt_topic);
	mosquitto_subscribe(mosq, NULL, mqtt_topic, 0);	
    }
}

void disconnect_callback(struct mosquitto* mosq, void* obj, int result) {
    fprintf(stderr, "Disconnected (status %d)\n", result);
}

void close_log_file() {
    if (log_fh)
	fclose(log_fh);
    log_fh = NULL;
}

FILE* open_log_file(struct tm* tm) {
    static int last_day = -1;
    char fname[32];
    
    if (log_fh == NULL || tm->tm_mday != last_day) {
	close_log_file();

	strftime(fname, sizeof(fname), "raw/%Y-%m-%d.txt", tm);
	fprintf(stderr, "Opening log file %s\n", fname);
	log_fh = fopen(fname, "a");
	if (!log_fh) {
	    perror("Error opening log file");
	    exit(1);
	}
	
	last_day = tm->tm_mday;
    }
    
    return log_fh;
}

void message_callback(struct mosquitto *mosq, void *obj, const struct mosquitto_message *message) {
    time_t now;
    char ts[32];
    FILE* f = NULL;
    struct tm* tm;

    /* Format time in ISO format */
    now = time(NULL);
    tm = gmtime(&now);
    strftime(ts, sizeof(ts), "%Y-%m-%dT%H:%M:%SZ", tm);

    /* Write entry to rotated log file */
    f = open_log_file(tm);
    if (fprintf(f, "%s,%s,%s\n", ts, message->topic, (char*)message->payload) < 0) {
	perror("Error writing log entry");
	exit(2);
    }
    fflush(f);
}

int main(int argc, char *argv[]) {
    char clientid[24];
    struct mosquitto *mosq;
    int rc = 0;

    mqtt_host = getenv2("MQTT_HOST", "localhost");
    mqtt_port = atoi(getenv2("MQTT_PORT", "1883"));
    mqtt_topic = getenv2("MQTT_TOPIC", "#");

    printf("Starting logger host=%s port=%d topic=%s\n", mqtt_host, mqtt_port, mqtt_topic);

    /*
    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);
    */

    mosquitto_lib_init();

    memset(clientid, 0, 24);
    snprintf(clientid, 23, "simplog-%d", getpid());
    mosq = mosquitto_new(clientid, true, NULL);
    
    if (mosq){
	mosquitto_connect_callback_set(mosq, connect_callback);
	mosquitto_disconnect_callback_set(mosq, disconnect_callback);
	mosquitto_message_callback_set(mosq, message_callback);

	printf("Connecting to MQTT host %s port %d\n", mqtt_host, mqtt_port);
	rc = mosquitto_connect(mosq, mqtt_host, mqtt_port, 60);
	
	while (run) {
	    rc = mosquitto_loop(mosq, -1, 1);
	    if (run && rc){
		fprintf(stderr, "Error %d, Reconnecting in 20s\n", rc);
		sleep(20);
		fprintf(stderr, "Reconnecting\n");
		mosquitto_reconnect(mosq);
	    }
	}
	mosquitto_destroy(mosq);
    } else {
	perror("Error initializing MQTT");
	rc = 3;
    }
    
    mosquitto_lib_cleanup();
    close_log_file();

    return rc;
}

