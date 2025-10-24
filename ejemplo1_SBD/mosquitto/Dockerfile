FROM eclipse-mosquitto:2

COPY passwd.sh /usr/local/bin/passwd.sh
RUN chmod +x /usr/local/bin/passwd.sh

ENV MOSQUITTO_USERNAME=""
ENV MOSQUITTO_PASSWORD=""

ENTRYPOINT ["/usr/local/bin/passwd.sh"]

CMD ["mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]
