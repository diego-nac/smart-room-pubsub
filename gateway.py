from source.gateway.Gateway import app, start_rabbitmq_consumers

if __name__ == "__main__":
    start_rabbitmq_consumers()
    app.run(debug=True, host='0.0.0.0', port=8080)