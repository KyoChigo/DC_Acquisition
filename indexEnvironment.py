import math
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

holiday = [datetime.date(2024, 4, 4) + datetime.timedelta(days=int(day)) for day in range(2)] \
        + [datetime.date(2024, 5, 1) + datetime.timedelta(days=int(day)) for day in range(4)] \
        + [datetime.date(2024, 6, 8) + datetime.timedelta(days=int(day)) for day in range(2)] \
        + [datetime.date(2024, 9, 15) + datetime.timedelta(days=int(day)) for day in range(2)] \
        + [datetime.date(2024, 10, 1) + datetime.timedelta(days=int(day)) for day in range(6)]

def is_weekend(date):
    "判断是否为周末"
    return date.weekday() >= 5

def Gauss(x, mu, sigma):
    "正规化Gauss分布"
    return math.exp(-(x - mu) ** 2 / (2 * sigma ** 2)) / (sigma * math.sqrt(2 * math.pi))

def superGauss(x, mu, sigma):
    "超级Gauss分布"
    n = 3
    return math.exp(-((x - mu) ** (2 * n)) / (2 * sigma ** 2))

def indexEnvi(time_list):
    "物价环境指数"
    alpha = 0.15
    beta = 0.075
    index_list = []
    for time in time_list:
        index = 1
        index -= alpha * superGauss(time, 31, 16 ** 4)
        index -= alpha * superGauss(time, 211, 16 ** 4)
        index -= alpha * superGauss(time, 365 + 31, 16 ** 4)    # 确保函数周期性
        index -= beta * superGauss(time, 277, 2.4 ** 4) # 国庆小长假
        date = datetime.date(2024, 1, 1) + datetime.timedelta(days=int(time))
        if date in holiday and date not in [datetime.date(2024, 10, 1) + datetime.timedelta(days=int(day)) for day in range(6)]:
            index *= 0.95   # 小假期物价下调
        elif is_weekend(date) and date not in [datetime.date(2024, 10, 1) + datetime.timedelta(days=int(day)) for day in range(6)]:
            index *= 0.98   # 周末物价下调
        index_list.append(index)
    
    return index_list

time_values = list(range(1, 366))
dates = [datetime.date(2024, 1, 1) + datetime.timedelta(days=int(day)) for day in time_values]
index_values = indexEnvi(time_values)

plt.figure(figsize=(15, 6))
plt.scatter(dates, index_values, label='indexEnvi(time)', color='b', s=3)
plt.title('Plot of indexEnvi(time)')
plt.xlabel('date')
plt.ylabel('environmental index')
plt.xlim(datetime.date(2024, 1, 1), datetime.date(2024, 12, 31))
plt.ylim(0.7, 1.1)
plt.grid(True)
plt.legend()
plt.xticks(rotation=45)
plt.show()
