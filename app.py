from flask import Flask, render_template, request
import datetime
from datetime import datetime, timedelta
import requests
from json import JSONDecodeError

app = Flask(__name__)

API_ECB_URL = 'https://api.exchangeratesapi.io/{}'
API_NBP_URL = 'http://api.nbp.pl/api/exchangerates/rates/{}/{}/{}/'


def adjust_day(day):
    if day.weekday() == 5:
        return day - timedelta(days=1)
    elif day.weekday() == 6:
        return day - timedelta(days=2)
    else:
        return day


def requests_ecb(b_currency, q_currency, start_date, end_date):
    day_count = (end_date - start_date).days + 1
    rates_list = []
    for d in (start_date + timedelta(n) for n in range(day_count)):
        r_ecb = requests.get(
            API_ECB_URL.format(d.strftime('%Y-%m-%d')),
            params={'base': b_currency, 'symbols': q_currency},
        )
        r_json = r_ecb.json()
        rates_list.append((d.strftime('%Y-%m-%d'), r_json['rates'][q_currency]))
    return rates_list


def request_nbp_json(currency, day):
    r_json = None
    while not r_json:
        try:
            r_nbp = requests.get(
                API_NBP_URL.format('a', currency,
                                   day.strftime('%Y-%m-%d')),
                params={'format': 'json'},
            )
            r_json = r_nbp.json()
        except JSONDecodeError:
            day = day - timedelta(days=1)
    return r_json


def requests_nbp(b_currency, q_currency, start_date, end_date):
    day_count = (end_date - start_date).days + 1
    rates_list = []
    for d in (start_date + timedelta(n) for n in range(day_count)):
        if b_currency == q_currency:
            rates_list.append((d.strftime('%Y-%m-%d'), 1.0))
        elif b_currency == 'PLN' or q_currency == 'PLN':
            r_json = request_nbp_json(b_currency if q_currency == 'PLN' else q_currency,
                                      adjust_day(d))
            rate = r_json['rates'][0]['mid']
            rates_list.append((d.strftime('%Y-%m-%d'), rate if q_currency == 'PLN' else 1 / rate))
        else:
            r_b_json = request_nbp_json(b_currency, adjust_day(d))
            r_q_json = request_nbp_json(q_currency, adjust_day(d))
            rates_list.append(
                (d.strftime('%Y-%m-%d'), r_b_json['rates'][0]['mid'] / r_q_json['rates'][0]['mid']))
    return rates_list


def min_max_avg_rate(rates_list):
    min_day_rate = min(rates_list, key=lambda rate: rate[1])
    max_day_rate = max(rates_list, key=lambda rate: rate[1])
    avg_rate = sum([rate[1] for rate in rates_list]) / float(len(rates_list))
    return min_day_rate, max_day_rate, avg_rate


def get_stats_page(b_currency, q_currency, start_date, end_date, rates_ecb, rates_nbp):
    min_ecb_rate, max_ecb_rate, avg_ecb_rate = min_max_avg_rate(rates_ecb)
    min_nbp_rate, max_nbp_rate, avg_nbp_rate = min_max_avg_rate(rates_nbp)
    rates = map(
        lambda rd_ecb, rd_nbp: (
            rd_ecb[0], '%.5f' % rd_ecb[1], '%.5f' % rd_nbp[1], '%.3f%%' % ((rd_ecb[1] - rd_nbp[1]) * 100 / rd_nbp[1])),
        rates_ecb, rates_nbp)

    return render_template('stats.html',
                           b_currency=b_currency,
                           q_currency=q_currency,
                           start_date=start_date.strftime('%Y-%m-%d'),
                           end_date=end_date.strftime('%Y-%m-%d'),
                           min_ecb_rate='%.5f' % min_ecb_rate[1],
                           min_ecb_day=min_ecb_rate[0],
                           max_ecb_rate='%.5f' % max_ecb_rate[1],
                           max_ecb_day=max_ecb_rate[0],
                           avg_ecb_rate='%.5f' % avg_ecb_rate,
                           min_nbp_rate='%.5f' % min_nbp_rate[1],
                           min_nbp_day=min_nbp_rate[0],
                           max_nbp_rate='%.5f' % max_nbp_rate[1],
                           max_nbp_day=max_nbp_rate[0],
                           avg_nbp_rate='%.5f' % avg_nbp_rate,
                           rates=rates,
                           )


def make_requests(b_currency, q_currency, start_date, end_date):
    rates_ecb = requests_ecb(b_currency, q_currency, start_date, end_date)
    rates_nbp = requests_nbp(b_currency, q_currency, start_date, end_date)
    return get_stats_page(b_currency, q_currency, start_date, end_date, rates_ecb, rates_nbp)


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
