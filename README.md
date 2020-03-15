# REST exercise
## Currency exchange rates

The basic app providing historical average exchange rates from European Central Bank and National Bank of Poland.

To deploy the app to local Gunicorn server, run:

```
$ gunicorn --bind 127.0.0.1:5000 app:app
```