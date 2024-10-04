#coding: utf-8
'''
第3代DC收购系统
- 制作: 南岛科学技术大学简明脚本研究所 Blues_Tkun
- 鸣谢: DC交通大学交达脚本研究院 kunjinkao_xs
        南岛科学技术大学简明脚本研究所 SlinkierApple13
'''

from dev.magicmq.pyspigot import PySpigot as ps # type: ignore
import org.bukkit.inventory # type: ignore
from org.bukkit.plugin.java import JavaPlugin # type: ignore
from org.bukkit import Bukkit, ChatColor # type: ignore
from com.earth2me.essentials import Essentials # type: ignore
from decimal import Decimal, ROUND_DOWN  # Essentials经济系统处理用
from util.anvilgui import anvilInputer # AnvilGUI
from net.wesjd.anvilgui import AnvilGUI # AnvilGUI Java Lib
import math
import random
from datetime import date, timedelta, datetime

historyDetail = ps.config.loadConfig('acquisition/historyDetail.yml')
historyMoney = ps.config.loadConfig('acquisition/historyMoney.yml')
Config = ps.config.loadConfig('acquisition/parameterConfig.yml')
historyMoneyDict = historyMoney.getValues(True)
ConfigDict = Config.getValues(True)

class calculate:
    def __init__(self):
        self.dictGoods = ["DIAMOND", "GOLD_INGOT", "IRON_INGOT", "COAL", "OAK_LOG", "BONE", "DIRT"]
        self.dictGoodsZh = ["钻石", "金锭", "铁锭", "煤炭", "橡木原木", "骨头", "泥土"]
        self.dictPrice = [20.00, 6.00, 1.50, 0.85, 1.00, 1.00, 0.06]
        self.dictEffic = [0.0004, 0.0004, 0.0004, 0.0003, 0.0002, 0.0002, 0.0016]
        self.holiday = [date(2024, 4, 4) + timedelta(days=int(day+1)) for day in range(2)] \
            + [date(2024, 5, 1) + timedelta(days=int(day+1)) for day in range(4)] \
            + [date(2024, 6, 8) + timedelta(days=int(day+1)) for day in range(2)] \
            + [date(2024, 9, 15) + timedelta(days=int(day+1)) for day in range(2)] \
            + [date(2024, 10, 1) + timedelta(days=int(day+1)) for day in range(6)]

    def calPrice(self, count=1, countHistory=0, priceInit=1.00, effic=0.0002, residue=0.00):
        totalPrice = Decimal('0.00')   # 总获益金额
        residue = Decimal(residue)
        overflow = False    # 判断是否超过本周期余额
        countSold = 0
        for i in range(count):
            priceNow = priceInit * math.exp(-effic*(i+countHistory+1))  # 当前单价
            priceNow = Decimal(priceNow).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
            if totalPrice + priceNow > residue:
                overflow = True
                break
            totalPrice += priceNow
            countSold += 1
        if countSold != 0:
            unitPrice = round(totalPrice / countSold, 2)
        else:
            unitPrice = Decimal('0.00')

        return [countSold, totalPrice, unitPrice, overflow]

    def calHistory(self, numberInit, t, g=1, tau=0.5):
        "numberInit: 初始数量, g: 逆时间系数(越大则临界点附近变化越剧烈), tau: 临界点"
        return int(math.floor(numberInit * (math.exp(g * (t - tau)) + 1) / (math.exp(g * (t + 1 - tau)) + 1)))
    
    def superGauss(self, x, mu, sigma):
        "超Gauss分布"
        return math.exp(-((x - mu) ** 6) / (2 * sigma ** 2))

    def randomAddictive(self):
        "Gauss噪音"
        sigma = 0.025
        return random.gauss(0, sigma)
    
    def indexEnvi(self, day):
        "物价环境指数"
        alpha = 0.15
        beta = 0.075
        
        index = 1
        index -= alpha * self.superGauss(day-1, 31, 16 ** 4)
        index -= alpha * self.superGauss(day-1, 211, 16 ** 4)
        index -= alpha * self.superGauss(day-1, 365 + 31, 16 ** 4)    # 确保函数周期性
        index -= beta * self.superGauss(day-1, 277, 2.4 ** 4) # 国庆小长假

        dayDate = date(2024, 1, 1) + timedelta(days=int(day-1))
        if dayDate in self.holiday and dayDate not in [date(2024, 10, 1) + timedelta(days=int(day-1)) for day in range(6)]:
            index *= 0.95   # 小假期物价下调
        elif dayDate.weekday() >= 5 and dayDate not in [date(2024, 10, 1) + timedelta(days=int(day-1)) for day in range(6)]:
            index *= 0.98   # 周末物价下调
        
        return index + self.randomAddictive()


def main(sender, label, args):
    player = sender.getPlayer()  # 获取玩家对象
    itemToSell = str(args[0])  # 收购物品
    itemID = calculate().dictGoods.index(itemToSell)
    itemToSellName = calculate().dictGoodsZh[itemID].decode('utf-8')

    if itemToSell in calculate().dictGoods:
        player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 欢迎来到&b" + itemToSellName + u"&a收购窗口！"))
        itemToSellNumber = 0  # 手中物品的总数
        # 遍历玩家的背包
        for item in player.getInventory().getContents():
            if item is not None and item.getType().toString() == itemToSell:
                itemToSellType = item.getType()
                itemToSellNumber += item.getAmount()

        if itemToSellNumber != 0:
            inputGUI = anvilInputer()
            itemNumHolder = [0]  # 使用列表保存itemNum

            def clickHandler(slot, stateSnapshot):
                if slot == AnvilGUI.Slot.OUTPUT: # GUI输入
                    text = stateSnapshot.getText() # 获取玩家输入
                    if text is not None:
                        try:
                            itemNumHolder[0] = int(text)
                        except ValueError:
                            player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&c 输入格式不正确！"))

                        if int(text) > itemToSellNumber: # 限制出售物品数量的上下限
                            player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&c 您只有&b" + str(itemToSellNumber) + u"个"
                                                                                    + itemToSellName + u"&a！"))
                            return [AnvilGUI.ResponseAction.replaceInputText(u"您没有那么多&b" + itemToSellName + u"&a！")]
                        elif int(text) <= 0:
                            return [AnvilGUI.ResponseAction.replaceInputText(u"不能设置非正数！")]
                        else:
                            return [AnvilGUI.ResponseAction.close()]
                        
                    else:
                        return [AnvilGUI.ResponseAction.replaceInputText(u"请输入出售数量")]
            inputGUI.onClick(clickHandler)
            
            # 设置关闭界面时的回调函数（必须是一个输入）
            def closeHandler(stateSnapshot):
                if itemNumHolder[0] >= 1 and itemNumHolder[0] <= itemToSellNumber:
                    historyDetailSection = historyDetail.getConfigurationSection(str(player.getName()))

                    if historyDetailSection is not None:   # 检查玩家是否有收购记录
                        tempDict = historyDetailSection.getValues(True)
                        residue = Decimal(str(tempDict["RESIDUE"]))
                        if itemToSell in tempDict.keys():
                            testHistory = sum(tempDict[itemToSell])
                        else:
                            testHistory = 0
                    else:
                        residue = Decimal('10000.00')   # 默认本周期剩余收购额度
                        tempDict = {"RESIDUE": residue}
                        testHistory = 0
                    itemNum = itemNumHolder[0]
                    testPriceInit = calculate().dictPrice[itemID]
                    testEffic = calculate().dictEffic[itemID]
                    calResult = calculate().calPrice(count=itemNum, priceInit=testPriceInit, effic=testEffic, countHistory=testHistory, residue=residue)
                    countSold = calResult[0]
                    testprice = calResult[1].quantize(Decimal('0.00'), rounding=ROUND_DOWN)
                    testUnitPrice = calResult[2]
                    overflow = calResult[3]

                    player.getInventory().removeItem(org.bukkit.inventory.ItemStack(itemToSellType, countSold)) # 删除出售物品
                    residue -= testprice
                    if countSold == 0:
                        player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 由于当前商品单价超过剩余收购额度，未能售出物品。"))
                    else:
                        if overflow:
                            player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 由于剩余收购额度不足，仅售出了一部分物品。"))
                        player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 售出&b" + str(countSold) + u"个" + itemToSellName
                                                                                + u"&a，获得&b" + str(testprice) + u" DC币&a！平均单价为&b" + str(testUnitPrice) + u" DC币&a。"))
                        player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 本周期剩余收购额度&b" + str(residue) + u" DC币&a。"))

                    tempDict["RESIDUE"] = residue
                    try:
                        tempDict[itemToSell][0] += countSold
                    except:
                        tempList = [int(countSold)] + [0 for _ in range(23)]
                        tempDict[itemToSell] = tempList
                    historyDetail.set(str(player.getName()), tempDict)
                    historyDetail.save()
                    
                    user = Bukkit.getServer().getPluginManager().getPlugin("Essentials").getUser(player)
                    user.giveMoney(testprice)
                    
                    # 将玩家获得DC币记录至长期数据库
                    cycleNow = ConfigDict["cycleNow"]
                    try:
                        tempInt = historyMoneyDict[str(cycleNow)][str(player.getName())]
                        tempInt += testprice
                    except:
                        tempInt = testprice
                    historyMoney.set(str(cycleNow)+"."+str(player.getName()), tempInt)
                    historyMoney.save()
                else:
                    player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 取消收购。"))

            inputGUI.onClose(lambda stateSnapshot : ps.scheduler.runTaskLater(closeHandler, 1, stateSnapshot)) # 重要：延迟1ticks再打开，否则不会触发Inventory事件！
            inputGUI.title(u"DC收购窗口")
            inputGUI.text(u"在此输入出售数量")
            inputGUI.open(player)

        else:
            player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&c 您背包内没有&b" + itemToSellName + u"&a！"))

    else:
        player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&c 物品不在收购范围内！"))
    
    return True


def newCycle(sender, label, args):
    player = sender.getPlayer()  # 获取玩家对象
    configDict = historyDetail.getValues(True)

    for sectionName in configDict:
        if "." not in sectionName:
            playerName = sectionName
            playerConfig = historyDetail.getConfigurationSection(str(sectionName)).getValues(True)

        elif str(sectionName)[len(playerName)+1:] in calculate().dictGoods:
            goodsName = str(sectionName)[len(playerName)+1:]
            section = playerConfig[goodsName]
            tempList = [0]
            for i in range(23):
                tempList.append(calculate().calHistory(section[i], t=i, g=0.7, tau=4))
            historyDetail.set(str(sectionName), tempList)

        elif str(sectionName)[len(playerName)+1:] == "RESIDUE": # 确定新周期余额，待补充
            historyDetail.set(str(sectionName), Decimal('10000.00'))
    
    Config.set("cycleNow", str(date.today()))
    Config.save()
    historyMoney.createSection(str(date.today()))
    historyMoney.save()
    player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 系统已进入新周期！"))

    return True


def indexEnviUpdate(sender, label, args):
    player = sender.getPlayer()  # 获取玩家对象
    today = Config.get('today')
    force = "FALSE"
    if len(args) == 1:
        force = str(args[0])
    if today != date.today().strftime("%Y-%m-%d") or force == "TRUE":
        todayIndex = Decimal(calculate().indexEnvi(int(datetime.strptime(today, '%Y-%m-%d').strftime('%j')))).quantize(Decimal('0.000'), rounding=ROUND_DOWN)
        Config.set('todayIndexEnvi', todayIndex)
        Config.set('today', str(date.today()))
        player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 新的一天，新的开始！今日价格环境指数为&b" + str(todayIndex) + u"&a！"))
        Config.save()
    else:
        player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 今日价格环境指数为&b" + str(Config.get('todayIndexEnvi')) + u"&a！"))
    
    return True


ps.command.registerCommand(main, "acquisition")
ps.command.registerCommand(newCycle, "newcycle")
ps.command.registerCommand(indexEnviUpdate, "newday")
