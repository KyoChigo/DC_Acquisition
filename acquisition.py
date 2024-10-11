#coding: utf-8
'''
第3代DC收购系统
- 制作: 南岛科学技术大学简明脚本研究所 Blues_Tkun
- 鸣谢: DC交通大学交达脚本研究院 kunjinkao_xs
        南岛科学技术大学简明脚本研究所 SlinkierApple13
        南岛科学技术大学简明脚本研究所 Sun_Yu_Xuan
'''

import math
import random
from decimal import Decimal, ROUND_DOWN
from datetime import date, timedelta, datetime
from dev.magicmq.pyspigot import PySpigot as ps # type: ignore
import org.bukkit.inventory # type: ignore
from org.bukkit.plugin.java import JavaPlugin # type: ignore
from org.bukkit import Bukkit, ChatColor, Material # type: ignore
from com.earth2me.essentials import Essentials # type: ignore
from util.anvilgui import anvilInputer # AnvilGUI
from util.gui import initializeGUI, initializeItemStack, spawnSeparators, guiHolder, closeGuiForAll
from net.wesjd.anvilgui import AnvilGUI # AnvilGUI Java Lib
from org.bukkit.event.inventory import InventoryClickEvent

temp_itemToSell = {}
temp_itemNum = {}

class calculate:
    def __init__(self):
        self.dictGoods = ["DIAMOND", "GOLD_INGOT", "IRON_INGOT", "COAL", "OAK_LOG", "BONE", "DIRT"]
        self.dictGoodsZh = ["钻石", "金锭", "铁锭", "煤炭", "橡木原木", "骨头", "泥土"]
        self.dictPrice = [20.00, 6.00, 1.50, 0.85, 1.00, 1.00, 0.06]
        self.dictEffic = [0.0004, 0.0004, 0.0004, 0.0003, 0.0002, 0.0002, 0.0016]
        self.Config = ps.config.loadConfig('acquisition/parameterConfig.yml')
        self.ConfigDict = self.Config.getValues(True)
        self.todayIndex = Decimal(self.Config.get('todayIndexEnvi'))
        self.historyMoney = ps.config.loadConfig('acquisition/historyMoney.yml')
        self.historyMoneyDict = self.historyMoney.getValues(True)
        self.historyDetail = ps.config.loadConfig('acquisition/historyDetail.yml')

    def calPrice(self, count=1, countHistory=0, priceInit=1.00, effic=0.0002, residue=0.00):
        "价格计算函数"
        totalPrice = Decimal('0.00')   # 总获益金额
        residue = Decimal(residue)  # 剩余收购额度
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
        
        totalPrice = Decimal(totalPrice * self.todayIndex).quantize(Decimal('0.00'), rounding=ROUND_DOWN)

        if countSold != 0:
            unitPrice = round(totalPrice / countSold, 2)
        else:
            unitPrice = Decimal('0.00')

        return [countSold, totalPrice, unitPrice, overflow]

    def priceQuery(self, countHistory=0, priceInit=1.00, effic=0.0002, residue=0.00, maxQuantity=64):
        "价格预览函数"
        totalPrice = Decimal('0.00')   # 总获益金额
        residue = Decimal(residue)  # 剩余收购额度
        overflow = False    # 判断是否超过本周期余额
        countMax = max(maxQuantity, 64) # maxQuantity为背包内当前物品总数
        priceQueryValue = []
        priceQueryOverflow = []
        priceQueryValueUnit = []

        for i in range(countMax):
            priceNow = priceInit * math.exp(-effic*(i+countHistory+1))  # 当前单价
            priceNow = Decimal(priceNow).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
            totalPrice += priceNow

            if overflow == False and totalPrice + priceNow > residue:
                overflow = True
            
            if i+1 in [1, 10, 64, countMax]:
                priceQueryValue.append(totalPrice)
                priceQueryOverflow.append(overflow)
                priceQueryValueUnit.append(Decimal(totalPrice/(i+1)).quantize(Decimal('0.00'), rounding=ROUND_DOWN))
        
        return priceQueryValue + priceQueryOverflow + priceQueryValueUnit

    def sellOut(self, player, itemToSell):
        historyDetailSection = self.historyDetail.getConfigurationSection(str(player.getName()))
        itemToSellType = Material.valueOf(itemToSell)
        itemID = self.dictGoods.index(itemToSell)
        itemToSellName = self.dictGoodsZh[itemID].decode('utf-8')

        if historyDetailSection is not None:   # 检查玩家是否有收购记录
            tempDict = historyDetailSection.getValues(True)
            residue = Decimal(str(tempDict["RESIDUE"]))
            if itemToSell in self.dictGoods:
                goodsHistory = sum(tempDict[itemToSell])
            else:
                goodsHistory = 0
        else:
            residue = NewCycleProcess().residueRenew()
            tempDict = {"RESIDUE": residue}
            goodsHistory = 0
            
        itemNum = temp_itemNum[player.getName()]
        priceInit = self.dictPrice[itemID]
        goodsEffic = self.dictEffic[itemID]
        calResult = self.calPrice(count=itemNum, priceInit=priceInit, effic=goodsEffic, countHistory=goodsHistory, residue=residue)
        countSold = calResult[0]
        goodsPrice = calResult[1].quantize(Decimal('0.00'), rounding=ROUND_DOWN)
        unitPrice = calResult[2]
        overflow = calResult[3]

        player.getInventory().removeItem(org.bukkit.inventory.ItemStack(itemToSellType, countSold)) # 删除出售物品
        residue -= goodsPrice
        if countSold == 0:
            player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 由于当前商品单价超过剩余收购额度，未能售出物品。"))
        else:
            if overflow:
                player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 由于剩余收购额度不足，仅售出了一部分物品。"))
            player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 售出&b" + str(countSold) + u"个" + itemToSellName
                                                                    + u"&a，获得&b" + str(goodsPrice) + u" DC币&a！平均单价为&b" + str(unitPrice) + u" DC币&a。"))
            player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 本周期剩余收购额度&b" + str(residue) + u" DC币&a。"))

        tempDict["RESIDUE"] = residue
        try:
            tempDict[itemToSell][0] += countSold
        except:
            tempList = [int(countSold)] + [0 for _ in range(23)]
            tempDict[itemToSell] = tempList
        self.historyDetail.set(str(player.getName()), tempDict)
        self.historyDetail.save()
        
        user = Bukkit.getServer().getPluginManager().getPlugin("Essentials").getUser(player)
        user.giveMoney(goodsPrice)
        
        # 将玩家获得DC币记录至长期数据库
        cycleNow = self.ConfigDict["cycleNow"]
        try:
            tempInt = Decimal(self.historyMoneyDict[str(cycleNow)+"."+str(player.getName())]).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
            tempInt += goodsPrice
        except:
            tempInt = goodsPrice
        self.historyMoney.set(str(cycleNow)+"."+str(player.getName()), tempInt)
        self.historyMoney.save()


class NewCycleProcess:
    "新周期处理用"
    def __init__(self):
        self.holiday = [date(2024, 4, 4) + timedelta(days=int(day+1)) for day in range(2)] \
            + [date(2024, 5, 1) + timedelta(days=int(day+1)) for day in range(4)] \
            + [date(2024, 6, 8) + timedelta(days=int(day+1)) for day in range(2)] \
            + [date(2024, 9, 15) + timedelta(days=int(day+1)) for day in range(2)] \
            + [date(2024, 10, 1) + timedelta(days=int(day+1)) for day in range(6)]

    def calHistory(self, numberInit, t, g=1, tau=0.5):
        "新周期历史记录衰减计算函数；numberInit: 初始数量, g: 逆时间系数(越大则临界点附近变化越剧烈), tau: 临界点"
        return int(math.floor(numberInit * (math.exp(g * (t - tau)) + 1) / (math.exp(g * (t + 1 - tau)) + 1)))
    
    def superGauss(self, x, mu, sigma):
        "超Gauss分布"
        return math.exp(-((x - mu) ** 6) / (2 * sigma ** 2))

    def randomAddictive(self):
        "Gauss噪音"
        sigma = 0.025
        return random.gauss(0, sigma)
    
    def indexEnvi(self, day):
        "物价环境指数计算函数"
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

    def residueRenew(self):
        "新周期各玩家收购额度计算函数"
        return Decimal("5000.00")


class GUIselect:
    def __init__(self, player, itemToSell):
        self.player = player
        self.historyDetailSection = historyDetail.getConfigurationSection(str(self.player.getName()))
        self.itemToSell = itemToSell
        self.itemToSellNumber = 0  # 收购物品的总数
        # 遍历玩家的背包
        for item in player.getInventory().getContents():
            if item is not None and item.getType().toString() == self.itemToSell:
                self.itemToSellType = item.getType()
                self.itemToSellNumber += item.getAmount()
        self.itemID = calculate().dictGoods.index(self.itemToSell)
        self.itemToSellName = calculate().dictGoodsZh[self.itemID].decode('utf-8')
        self.historyMoney = ps.config.loadConfig('acquisition/historyMoney.yml')
        self.historyMoneyDict = self.historyMoney.getValues(True)
        self.historyDetail = ps.config.loadConfig('acquisition/historyDetail.yml')

    def canSell(self):
        if self.itemToSellNumber != 0:
            return True
        else:
            return False

    def open(self):
        if self.historyDetailSection is not None:   # 检查玩家是否有收购记录
            tempDict = self.historyDetailSection.getValues(True)
            residue = Decimal(str(tempDict["RESIDUE"]))
            if self.itemToSell in tempDict.keys():
                goodsHistory = sum(tempDict[self.itemToSell])
            else:
                goodsHistory = 0
        else:
            goodsHistory = 0
            residue = NewCycleProcess().residueRenew()
        
        priceInit = calculate().dictPrice[self.itemID]
        goodsEffic = calculate().dictEffic[self.itemID]

        priceQueryList = calculate().priceQuery(countHistory=goodsHistory, priceInit=priceInit, effic=goodsEffic, residue=residue, maxQuantity=self.itemToSellNumber)

        selectGUI = initializeGUI("acq.select", 9, u"DC收购窗口：" + self.itemToSellName)
        selectGUI.setItem(0, initializeItemStack(Material.valueOf(self.itemToSell), u"§a当前收购物品：§b" + self.itemToSellName))
        selectGUI.setItem(8, initializeItemStack(Material.RED_WOOL, u"§c取消收购"))
        selectGUI.setItem(2, initializeItemStack(Material.GOLD_NUGGET, u"§a出售1个", "", u"§f预计总价：" + str(priceQueryList[0]), 
                                                  u"§f预计单价：" + str(priceQueryList[8]), u"§c超出本周期剩余收购额度" if str(priceQueryList[4]) == True else u"§a可出售"))
        selectGUI.setItem(3, initializeItemStack(Material.GOLD_INGOT, u"§a出售10个", "", u"§f预计总价：" + str(priceQueryList[1]),
                                                  u"§f预计单价：" + str(priceQueryList[9]), u"§c超出本周期剩余收购额度" if str(priceQueryList[5]) == True else u"§a可出售"))
        selectGUI.setItem(4, initializeItemStack(Material.GOLD_BLOCK, u"§a出售64个", "", u"§f预计总价：" + str(priceQueryList[2]),
                                                  u"§f预计单价：" + str(priceQueryList[10]), u"§c超出本周期剩余收购额度" if str(priceQueryList[6]) == True else u"§a可出售"))
        selectGUI.setItem(5, initializeItemStack(Material.BARREL, u"§a出售背包内全部（§b" + str(self.itemToSellNumber) + u"个§a）",
                                                  "", u"§f预计总价：" + str(priceQueryList[3]),
                                                  u"§f预计单价：" + str(priceQueryList[11]), u"§c超出本周期剩余收购额度" if str(priceQueryList[7]) == True else u"§a可出售"))
        selectGUI.setItem(6, initializeItemStack(Material.LEGACY_BOOK_AND_QUILL, u"§a自定义出售", "", u"§e注意：无法预览价格"))
        spawnSeparators(selectGUI, 1, 1) # 挡板
        spawnSeparators(selectGUI, 7, 7) # 挡板

        return selectGUI

    def handler(self, e):
        clickInt = e.getSlot()
        if clickInt == 2:
            temp_itemNum[self.player.getName()] = 1
            calculate().sellOut(player=self.player, itemToSell=self.itemToSell)
            self.player.closeInventory()
        elif clickInt == 3:
            temp_itemNum[self.player.getName()] = 10
            calculate().sellOut(player=self.player, itemToSell=self.itemToSell)
            self.player.closeInventory()
        elif clickInt == 4:
            temp_itemNum[self.player.getName()] = 64
            calculate().sellOut(player=self.player, itemToSell=self.itemToSell)
            self.player.closeInventory()
        elif clickInt == 5:
            temp_itemNum[self.player.getName()] = self.itemToSellNumber
            calculate().sellOut(player=self.player, itemToSell=self.itemToSell)
            self.player.closeInventory()
        elif clickInt == 6:
            GUIinput(self.player, self.itemToSell).open()
        elif clickInt == 8:
            self.player.closeInventory()
        else:
            e.setCancelled(True)
        
        return True


class GUIinput(GUIselect):
    def __init__(self, player, itemToSell):
        GUIselect.__init__(self, player, itemToSell)
        self.inputGUI = anvilInputer()

    def open(self):
        self.inputGUI.onClick(self.clickHandler)
        self.inputGUI.onClose(lambda stateSnapshot: ps.scheduler.runTaskLater(lambda: self.closeHandler(self), 1, stateSnapshot)) # 重要：延迟1ticks再打开，否则不会触发Inventory事件！
        self.inputGUI.title(u"DC收购窗口：" + self.itemToSellName)
        self.inputGUI.text(u"输入数量 (您有" + str(self.itemToSellNumber) + u"个)")
        self.inputGUI.open(self.player)

    def clickHandler(self, slot, stateSnapshot):
        if slot == AnvilGUI.Slot.OUTPUT: # GUI输入
            text = stateSnapshot.getText() # 获取玩家输入
            if text is not None:
                try:
                    temp_itemNum[self.player.getName()] = int(text)
                except ValueError:
                    return [AnvilGUI.ResponseAction.replaceInputText(u"输入格式不正确！")]

                if int(text) > self.itemToSellNumber: # 限制出售物品数量的上下限
                    self.player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&c 您只有&b" + str(self.itemToSellNumber) + u"个"
                                                                            + self.itemToSellName + u"&a！"))
                    return [AnvilGUI.ResponseAction.replaceInputText(u"您没有那么多" + self.itemToSellName + u"！")]
                elif int(text) <= 0:
                    return [AnvilGUI.ResponseAction.replaceInputText(u"不能设置非正数！")]
                else:
                    return [AnvilGUI.ResponseAction.close()]
            else:
                return [AnvilGUI.ResponseAction.replaceInputText(u"请输入出售数量")]

    def closeHandler(self, stateSnapshot):
        if temp_itemNum[self.player.getName()] >= 1 and temp_itemNum[self.player.getName()] <= self.itemToSellNumber:
            calculate().sellOut(player=self.player, itemToSell=self.itemToSell)
        else:
            self.player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 取消收购。"))


def main(sender, label, args):
    "收购主函数"
    player = sender.getPlayer()  # 获取玩家对象
    itemToSell = str(args[0])  # 收购物品
    itemID = calculate().dictGoods.index(itemToSell)
    itemToSellName = calculate().dictGoodsZh[itemID].decode('utf-8')

    if itemToSell in calculate().dictGoods:
        player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 欢迎来到&b" + itemToSellName + u"&a收购窗口！"))
        GUI = GUIselect(player, itemToSell)
        if GUI.canSell():
            temp_itemToSell[player.getName()] = itemToSell
            player.openInventory(GUIselect(player, itemToSell).open())
        else:
            player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&c 您背包内没有&b" + itemToSellName + u"&a！"))
    else:
        player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&c 物品不在收购范围内！"))
    
    return True


def newCycle(sender, label, args):
    "新周期执行函数"
    player = sender.getPlayer()  # 获取玩家对象
    historyDetail = ps.config.loadConfig('acquisition/historyDetail.yml')
    historyDetailDict = historyDetail.getValues(True)
    historyMoney = ps.config.loadConfig('acquisition/historyMoney.yml')
    historyMoneyDict = historyMoney.getValues(True)
    Config = ps.config.loadConfig('acquisition/parameterConfig.yml')

    for sectionName in historyDetailDict:
        if "." not in sectionName:
            playerName = sectionName
            playerConfig = historyDetail.getConfigurationSection(str(sectionName)).getValues(True)
        elif str(sectionName)[len(playerName)+1:] in calculate().dictGoods:
            goodsName = str(sectionName)[len(playerName)+1:]
            section = playerConfig[goodsName]
            tempList = [0]
            for i in range(23):
                tempList.append(NewCycleProcess().calHistory(section[i], t=i, g=0.7, tau=4))
            historyDetail.set(str(sectionName), tempList)
        elif str(sectionName)[len(playerName)+1:] == "RESIDUE": # 确定新周期余额
            historyDetail.set(str(sectionName), NewCycleProcess().residueRenew())
    
    historyDetail.save()
    Config.set("cycleNow", str(date.today()))
    Config.save()
    if str(date.today()) not in historyMoneyDict.keys():
        historyMoney.createSection(str(date.today()))
    historyMoney.save()
    player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 系统已进入新周期！"))

    return True


def indexEnviUpdate(sender, label, args):
    "价格环境指数更新函数"
    player = sender.getPlayer()
    Config = ps.config.loadConfig('acquisition/parameterConfig.yml')
    today = Config.get('today')
    force = "FALSE"
    if len(args) == 1:
        force = str(args[0])

    if today != date.today().strftime("%Y-%m-%d") or force == "TRUE":
        yesterdayIndex = Decimal(Config.get('todayIndexEnvi')).quantize(Decimal('0.000'))
        todayIndex = Decimal(NewCycleProcess().indexEnvi(int(datetime.strptime(today, '%Y-%m-%d').strftime('%j')))).quantize(Decimal('0.000'), rounding=ROUND_DOWN)
        deltaIndex = todayIndex - yesterdayIndex

        Config.set('todayIndexEnvi', todayIndex)
        Config.set('today', str(date.today()))
        Config.save()

        player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 新的一天，新的开始！今日价格环境指数为&b" + str(todayIndex) + u"&a！"))
        if deltaIndex > Decimal('0.000'):
            player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 价格环境指数较昨日相比&b增加" + str(deltaIndex) + u"&a！"))
        elif deltaIndex < Decimal('0.000'):
            player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 价格环境指数较昨日相比&c减少" + str(deltaIndex) + u"&a！"))
        else:
            player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 价格环境指数较昨日未发生变化！"))
    else:
        player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 今日价格环境指数已经更新！当前指数为&b" + str(Decimal(Config.get('todayIndexEnvi')).quantize(Decimal('0.000'))) + u"&a！"))
    
    return True


def indexEnviQuery(sender, label, args):
    "价格环境指数查询函数"
    player = sender.getPlayer()
    player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 今日价格环境指数为&b" + str(Decimal(Config.get('todayIndexEnvi')).quantize(Decimal('0.000'))) + u"&a！"))
    
    return True


def onGUIOpen(e):
    inv = e.getInventory()
    invHolder = inv.getHolder()
    if isinstance(invHolder, guiHolder):
        player = e.getWhoClicked()
        invName = invHolder.getName()

        if invName.startswith("acq."):
            itemToSell = temp_itemToSell.get(player.getName())
            GUIselect(player, itemToSell).handler(e)


def stop():
    "关闭所有打开菜单的玩家"
    closeGuiForAll("acq.")


ps.command.registerCommand(main, "acquisition")
ps.command.registerCommand(newCycle, "newcycle")
ps.command.registerCommand(indexEnviUpdate, "newday")
ps.command.registerCommand(indexEnviQuery, "indexenvi")
ps.listener.registerListener(onGUIOpen, InventoryClickEvent, True)
