from flask import Flask, render_template, request
import datetime
from datetime import datetime, timedelta
import requests
import numpy as np

app = Flask(__name__)

API_ER_URL = 'https://api.exchangeratesapi.io/{}'
API_NBP_URL = 'http://api.nbp.pl/api/exchangerates/rates/{}/{}/{}/'


# TODO
# Average exchange rate
# Minimal exchange rate - with day
# Maximal exchange rate - with day

def adjust_day(day):
    if day.weekday() == 5:
        return day - timedelta(days=1)
    elif day.weekday() == 6:
        return day - timedelta(days=2)
    else:
        return day


def requests_er(b_currency, q_currency, start_date, end_date):
    day_count = (end_date - start_date).days + 1
    rates_list = []
    for d in (start_date + timedelta(n) for n in range(day_count)):
        r_er = requests.get(
            API_ER_URL.format(d.strftime('%Y-%m-%d')),
            params={'base': b_currency, 'symbols': q_currency},
        )
        r_json = r_er.json()
        rates_list.append((d, r_json['rates'][q_currency]))
    return rates_list


def requests_nbp(b_currency, q_currency, start_date, end_date):
    day_count = (end_date - start_date).days + 1
    rates_list = []
    for d in (start_date + timedelta(n) for n in range(day_count)):
        if b_currency == q_currency:
            rates_list.append((d, 1.0))
        elif b_currency == 'PLN' or q_currency == 'PLN':
            r_nbp = requests.get(
                API_NBP_URL.format('a', b_currency if q_currency == 'PLN' else q_currency,
                                   adjust_day(d).strftime('%Y-%m-%d')),
                params={'format': 'json'},
            )
            r_json = r_nbp.json()
            rate = r_json['rates'][0]['mid']
            rates_list.append((d, rate if q_currency == 'PLN' else 1 / rate))
        else:
            r_nbp_b = requests.get(
                API_NBP_URL.format('a', b_currency, adjust_day(d).strftime('%Y-%m-%d')),
                params={'format': 'json'},
            )
            r_b_json = r_nbp_b.json()
            r_nbp_q = requests.get(
                API_NBP_URL.format('a', q_currency, adjust_day(d).strftime('%Y-%m-%d')),
                params={'format': 'json'},
            )
            r_q_json = r_nbp_q.json()
            rates_list.append((d, r_b_json['rates'][0]['mid'] / r_q_json['rates'][0]['mid']))
    return rates_list


def min_max_avg_rate(rates_list):
    min_day_rate = min(rates_list, key=lambda rate: rate[1])
    max_day_rate = max(rates_list, key=lambda rate: rate[1])
    avg_rate = sum([rate[1] for rate in rates_list]) / float(len(rates_list))
    return min_day_rate, max_day_rate, avg_rate


def make_requests(b_currency, q_currency, start_date, end_date):
    rates_er = requests_er(b_currency, q_currency, start_date, end_date)
    rates_nbp = requests_nbp(b_currency, q_currency, start_date, end_date)
    print(min_max_avg_rate(rates_er))
    print(min_max_avg_rate(rates_nbp))
    return 'Hello!'


@app.route('/')
@app.route('/index.html')
def my_form():
    return render_template('index.html', today=datetime.today().strftime('%Y-%m-%d'))


@app.route('/stats', methods=['POST'])
def my_form_post():
    b_currency = request.form['base_currency']
    q_currency = request.form['quote_currency']
    date_type = request.form['date_type']
    if date_type == 'fixed':
        fixed_days = int(request.form['fixed_days'])
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=(fixed_days - 1))
    else:
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()

        if start_date > datetime.today().date():
            return render_template('error.html', error_msg='Start date must be no later than today.')
        if start_date > end_date:
            return render_template('error.html', error_msg='Start date must be before end date.')
        if 50 < (end_date - start_date).days or (end_date - start_date).days < 5:
            return render_template('error.html', error_msg='You must select between 5 to 50 days.')

    return make_requests(b_currency, q_currency, start_date, end_date)


if __name__ == '__main__':
    app.run()
