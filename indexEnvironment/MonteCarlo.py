import math
import random
import datetime
import matplotlib.pyplot as plt
import numpy as np

holiday = [datetime.date(2024, 4, 4) + datetime.timedelta(days=int(day)) for day in range(2)] \
        + [datetime.date(2024, 5, 1) + datetime.timedelta(days=int(day)) for day in range(4)] \
        + [datetime.date(2024, 6, 8) + datetime.timedelta(days=int(day)) for day in range(2)] \
        + [datetime.date(2024, 9, 15) + datetime.timedelta(days=int(day)) for day in range(2)] \
        + [datetime.date(2024, 10, 1) + datetime.timedelta(days=int(day)) for day in range(6)]

def is_weekend(date):
    "判断是否为周末"
    return date.weekday() >= 5

def superGauss(x, mu, sigma):
    "超级Gauss分布"
    n = 3
    return math.exp(-((x - mu) ** (2 * n)) / (2 * sigma ** 2))

def randomAddictive(sigma):
    "Gauss噪音"
    return random.gauss(0, sigma)

def indexEnvi(time_list, noise=False):
    "无噪音物价环境指数"
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
        
        if noise:
            index_list.append(index + randomAddictive(sigma))
        else:
            index_list.append(index)
    
    return index_list

sigma = 0.025
num_simulations = 10000  # 蒙特卡洛模拟次数
days_in_year = 365
simulated_data = np.zeros((days_in_year, num_simulations))

for i in range(num_simulations):
    time_values = list(range(1, days_in_year + 1))
    daily_values = indexEnvi(time_values, noise=True)
    simulated_data[:, i] = daily_values  # 将每次模拟结果存储到数组中

time_values = list(range(1, 366))
dates = [datetime.date(2024, 1, 1) + datetime.timedelta(days=int(day)) for day in time_values]
index_values = indexEnvi(time_values)
mean_index = np.array(index_values)
index_values_1sigma = np.array(index_values) + sigma
index_values_m1sigma = np.array(index_values) - sigma
index_values_2sigma = np.array(index_values) + sigma*2
index_values_m2sigma = np.array(index_values) - sigma*2

# 生成二维频度图
plt.figure(figsize=(15, 6))
plt.hist2d(np.tile(np.arange(1, days_in_year + 1), num_simulations),
           simulated_data.flatten(order='F'),
           bins=[days_in_year, 100],
           cmap='viridis', density=True)
plt.title('Monte Carlo Simulation of indexEnvi (' + str(num_simulations) + ' iterations)')
plt.xlabel('Day of the year')
plt.ylabel('indexEnvi value')
plt.colorbar(label='Normalized Frequency')
plt.grid(True)
plt.plot(time_values, mean_index, color='yellow', linestyle='-', label='$\mu$', linewidth=1)
plt.plot(time_values, index_values_1sigma, color='orange', linestyle='-', label='$\mu \pm \sigma$', linewidth=1)
plt.plot(time_values, index_values_m1sigma, color='orange', linestyle='-', linewidth=1)
plt.plot(time_values, index_values_2sigma, color='lightcoral', linestyle='--', label='$\mu \pm 2\sigma$', linewidth=1)
plt.plot(time_values, index_values_m2sigma, color='lightcoral', linestyle='--', linewidth=1)
plt.legend()
plt.show()
