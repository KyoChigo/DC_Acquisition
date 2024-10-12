import math
import numpy as np
import matplotlib.pyplot as plt
from decimal import Decimal, ROUND_DOWN

def calPrice(count, countHistory, priceInit, effic):
    total = Decimal('0.00')   # 总获益金额
    for i in range(count):
        priceNow = Decimal(priceInit * math.exp(-effic*(i+countHistory+1))).quantize(Decimal('0.00'), rounding=ROUND_DOWN)  # 当前单价
        total += priceNow

    return [round(priceInit * math.exp(-effic*(count+countHistory)), 2), round(total, 2)]

priceUnit = []
priceTotal = []
countHistory = 0    # 历史售出数量
priceInit = 0.80    # 初始单价
effic = 0.000325    # 逆时间系数
stacks = 27         # 组数

print("组数", "单价", "总获益", "单价比例", sep="\t\t")
for i in range(stacks+1):
    temp = calPrice(count=64*i, countHistory=countHistory, priceInit=priceInit, effic=effic)
    priceUnit.append(temp[0])
    priceTotal.append(temp[1])
    if temp[0] == 0:
        break
    print(i, temp[0], temp[1], f"{(temp[0]/priceInit * 100):.2f}%", sep="\t\t")

fig, ax1 = plt.subplots(figsize=(10, 6))

# 绘制总价格
ax1.plot(range(stacks+1), priceTotal, color='b', label='Total Price')
ax1.scatter(range(stacks+1), priceTotal, color='b', s=10)
ax1.set_title(f'Total and Unit Price ($p_0 = {priceInit}, \delta = {effic}$)')
ax1.set_xlabel('Number of Stack')
ax1.set_ylabel('Total Price', color='b')
ax1.set_xlim(0, stacks)
ax1.set_ylim(0, float(max(priceTotal)) * 1.1)
ax1.tick_params(axis='y', labelcolor='b')
ax1.grid(True)

# 绘制单价
ax2 = ax1.twinx()
ax2.plot(range(stacks+1), priceUnit, color='r', linestyle='--', label='Unit Price')
ax2.scatter(range(stacks+1), priceUnit, color='r', s=10)
ax2.set_ylabel('Unit Price', color='r')
ax2.set_ylim(0, max(priceUnit) * 1.1)
ax2.tick_params(axis='y', labelcolor='r')

# 添加辅助线
slopes = []
for i in range(11):
    slopes.append(-i * 0.1 * priceInit / stacks)

for i, slope in enumerate(slopes):
    y_values = [priceInit + slope * x for x in range(stacks+1)]
    ax2.plot(range(stacks+1), y_values, color='gray', linestyle='--', linewidth=0.5)

fig.tight_layout()
plt.show()
