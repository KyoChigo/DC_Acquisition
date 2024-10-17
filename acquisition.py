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
from me.clip.placeholderapi import PlaceholderAPI # DC交通大学活跃脉冲接口用

temp_itemToSell = {}
temp_itemNum = {}

class calculate:
    def __init__(self):
        self.dictGoods = ["DIAMOND", "GOLD_INGOT", "IRON_INGOT", "COAL", "OAK_LOG", "BONE", "DIRT"]
        self.dictGoodsZh = ["钻石", "金锭", "铁锭", "煤炭", "橡木原木", "骨头", "泥土"]
        self.dictPrice = [8.20, 4.25, 1.75, 0.75, 0.80, 1.00, 0.06]
        self.dictEffic = [0.000500, 0.000425, 0.000375, 0.000325, 0.000300, 0.000325, 0.000750]
        self.Config = ps.config.loadConfig('acquisition/parameterConfig.yml')
        self.ConfigDict = self.Config.getValues(True)
        self.todayIndex = Decimal(self.Config.get('todayIndexEnvi')).quantize(Decimal('0.000'))
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
            priceNow = Decimal(priceInit * math.exp(-effic*(i+countHistory+1)))  # 当前单价
            priceNow = Decimal(priceNow * self.todayIndex).quantize(Decimal('0.00'), rounding=ROUND_DOWN)

            if totalPrice + priceNow > residue:
                overflow = True
                break

            totalPrice += priceNow
            countSold += 1
        
        totalPrice = Decimal(totalPrice).quantize(Decimal('0.00'), rounding=ROUND_DOWN)

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
        priceQueryValue = [-1, -1, -1, -1]
        priceQueryOverflow = [False, False, False, False]
        priceQueryValueUnit = [-1, -1, -1, -1]
        priceQueryOverflowNum = [-1]

        for i in range(maxQuantity):
            priceNow = Decimal(priceInit * math.exp(-effic*(i+countHistory+1)))  # 当前单价
            priceNow = Decimal(priceNow * self.todayIndex).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
            totalPrice += priceNow

            if overflow == False and totalPrice > residue:
                overflow = True
                priceQueryOverflowNum.append(i)
            
            itemNum = [1, 10, 64]
            if i+1 in itemNum:
                priceQueryValue[itemNum.index(i+1)] = totalPrice
                priceQueryOverflow[itemNum.index(i+1)] = overflow
                priceQueryValueUnit[itemNum.index(i+1)] = Decimal(totalPrice/(i+1)).quantize(Decimal('0.00'), rounding=ROUND_DOWN)

            if i+1 == maxQuantity:
                priceQueryValue[3] = totalPrice
                priceQueryOverflow[3] = overflow
                priceQueryValueUnit[3] = Decimal(totalPrice/(i+1)).quantize(Decimal('0.00'), rounding=ROUND_DOWN)

        return priceQueryValue + priceQueryOverflow + priceQueryValueUnit + priceQueryOverflowNum

    def sellOut(self, player, itemToSell):
        historyDetailSection = self.historyDetail.getConfigurationSection(str(player.getName()))
        itemToSellType = Material.valueOf(itemToSell)
        itemID = self.dictGoods.index(itemToSell)
        itemToSellName = self.dictGoodsZh[itemID].decode('utf-8')

        if historyDetailSection is not None:   # 检查玩家是否有收购记录
            tempDict = historyDetailSection.getValues(True)
            residue = Decimal(str(tempDict["RESIDUE"]))
            if itemToSell in tempDict:
                goodsHistory = sum(tempDict[itemToSell])
            else:
                goodsHistory = 0
        else:
            residue = NewCycleProcess().residueRenew(player)
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
        self.holidayShort = [date(2024, 4, 4) + timedelta(days=int(day+1)) for day in range(2)] \
            + [date(2024, 5, 1) + timedelta(days=int(day+1)) for day in range(4)] \
            + [date(2024, 6, 8) + timedelta(days=int(day+1)) for day in range(2)] \
            + [date(2024, 9, 15) + timedelta(days=int(day+1)) for day in range(2)] \
            + [date(2024, 10, 1) + timedelta(days=int(day+1)) for day in range(6)]  # 中小假期
        self.holidayLong = [date(2024, 1, 1) + timedelta(days=int(day+1)) for day in range(60)] \
            + [date(2024, 7, 1) + timedelta(days=int(day+1)) for day in range(60)]  # 长假期
        self.activityDetail = ps.config.loadConfig('acquisition/activityDetail.yml')
        self.activityDetailDict = self.activityDetail.getValues(True)
        self.historyDetail = ps.config.loadConfig('acquisition/historyDetail.yml')

    def calHistory(self, numberInit, t, g=1, tau=0.5):
        "新周期历史记录衰减计算函数；numberInit: 初始数量, g: 逆时间系数(越大则临界点附近变化越剧烈), tau: 临界点"
        return int(math.floor(numberInit * (math.exp(g * (t - tau)) + 1) / (math.exp(g * (t + 1 - tau)) + 1)))
    
    def superGauss(self, x, mu, sigma):
        "超Gauss分布"
        return math.exp(-((x - mu) ** 6) / (2 * sigma ** 2))

    def randomAddictive(self, sigma, amp):
        "Gauss噪音"
        return random.gauss(0, sigma) * amp
    
    def indexEnvi(self, day, alpha=0.150, beta=0.075):
        "物价环境指数计算函数"
        index = 1
        index -= alpha * self.superGauss(day-1, 31, 16 ** 4)
        index -= alpha * self.superGauss(day-1, 211, 16 ** 4)
        index -= alpha * self.superGauss(day-1, 365 + 31, 16 ** 4)    # 确保函数周期性
        index -= beta * self.superGauss(day-1, 277, 2.4 ** 4) # 国庆小长假

        dayDate = date(2024, 1, 1) + timedelta(days=int(day-1))
        if dayDate in self.holidayShort and dayDate not in [date(2024, 10, 1) + timedelta(days=int(day-1)) for day in range(6)]:
            index *= 0.95   # 小假期物价下调
        elif dayDate.weekday() >= 5 and dayDate not in [date(2024, 10, 1) + timedelta(days=int(day-1)) for day in range(6)]:
            index *= 0.98   # 周末物价下调
        
        return index + self.randomAddictive(sigma=0.025, amp=1)

    def residueActivity(self, activity):
        "收购额度中活跃额度的计算函数"
        current_day = datetime.now()
        if current_day in self.holidayLong: # 旺季
            return Decimal(min(activity * 125, 5000)).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
        else:   # 淡季
            return Decimal(min(activity * 300, 6000)).quantize(Decimal('0.00'), rounding=ROUND_DOWN)

    def residueRenew(self, player):
        "新周期各玩家收购额度计算函数"
        historyDetailSection = self.historyDetail.getConfigurationSection(str(player.getName()))
        historyDetailSectionDict = historyDetailSection.getValues(True)

        current_day = datetime.now()
        last_month = (current_day.replace(day=1) - timedelta(days=1)).strftime("%Y/%m")
        this_month = current_day.strftime("%Y/%m")

        if current_day in self.holidayLong: # 旺季
            residueBasic = Decimal(3000 + self.randomAddictive(sigma=0.065, amp=16000)).quantize(Decimal('0.00'), rounding=ROUND_DOWN) # 基础额度
        else:   # 淡季
            residueBasic = Decimal(4000 + self.randomAddictive(sigma=0.040, amp=10000)).quantize(Decimal('0.00'), rounding=ROUND_DOWN) # 基础额度

        activityPlayerNow = activity(player).getPlayerHot(this_month)
        if activityPlayerNow != -1: # 若服务器中存在DC交通大学活跃脉冲记录
            try:
                activityPlayerLastCycle = historyDetailSectionDict[str(player.getName())]
            except:
                activityPlayerLastCycle = 0

            activityPlayerTotal = activityPlayerNow
            if this_month != str(self.activityDetailDict["updateLatest"]):  # 跨月处理
                activityPlayerLastMonth = activity(player).getPlayerHot(last_month)
                activityPlayerTotal += activityPlayerLastMonth
                self.activityDetail.set("updateLatest", this_month)
            
            self.activityDetail.set(str(player.getName()), Decimal(activityPlayerNow).quantize(Decimal('0'), rounding=ROUND_DOWN))
            activityPlayer = activityPlayerTotal - activityPlayerLastCycle
            residue = residueBasic + self.residueActivity(activityPlayer)
            self.activityDetail.save()

        else:   # 本机测试模式
            residue = residueBasic
    
        return residue


class activity:
    "DC交通大学活跃脉冲计算用"
    def __init__(self, player):
        self.player = player

    def getPapi(self, placeholder):
        return PlaceholderAPI.setPlaceholders(self.player, "%" + placeholder + "%")

    def getPlayerHot(self, month):
        "month格式：YYYY/MM"
        try:
            return int(self.getPapi(self.player, "javascript_geoloc_api,playerHotTotal,{player_name},"+month))
        except:
            return -1   # 本机测试模式
        

class GUIselect:
    def __init__(self, player, itemToSell):
        self.player = player
        self.historyDetail = ps.config.loadConfig('acquisition/historyDetail.yml')
        self.historyDetailSection = self.historyDetail.getConfigurationSection(str(self.player.getName()))
        self.historyMoney = ps.config.loadConfig('acquisition/historyMoney.yml')
        self.historyMoneyDict = self.historyMoney.getValues(True)
        self.Config = ps.config.loadConfig('acquisition/parameterConfig.yml')
        self.todayIndex = Decimal(self.Config.get('todayIndexEnvi')).quantize(Decimal('0.000'))

        self.itemToSell = itemToSell
        self.itemToSellNumber = 0  # 收购物品的总数
        # 遍历玩家的背包
        for item in player.getInventory().getContents():
            if item is not None and item.getType().toString() == self.itemToSell:
                if item.hasItemMeta() == False:
                    self.itemToSellType = item.getType()
                    self.itemToSellNumber += item.getAmount()
        self.itemID = calculate().dictGoods.index(self.itemToSell)
        self.itemToSellName = calculate().dictGoodsZh[self.itemID].decode('utf-8')

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
            residue = NewCycleProcess().residueRenew(self.player)
        
        priceInit = calculate().dictPrice[self.itemID]
        goodsEffic = calculate().dictEffic[self.itemID]

        priceQueryList = calculate().priceQuery(countHistory=goodsHistory, priceInit=priceInit, effic=goodsEffic, residue=residue, maxQuantity=self.itemToSellNumber)

        selectGUI = initializeGUI("acq.select", 9, u"DC收购窗口：" + self.itemToSellName)
        selectGUI.setItem(0, initializeItemStack(Material.valueOf(self.itemToSell), u"§a当前收购物品：§b" + self.itemToSellName,
                                                  u"§a今日价格环境指数：§b" + str(self.todayIndex), u"§a当前剩余收购额度：§b" + str(residue) + u" DC币"))
        selectGUI.setItem(8, initializeItemStack(Material.RED_WOOL, u"§c取消收购"))
        selectGUI.setItem(2, initializeItemStack(Material.GOLD_NUGGET, u"§a出售1个", "", u"§f预计总价：" + str(priceQueryList[0]) + u" DC币", 
                                                  u"§f对应单价：" + str(priceQueryList[8]) + u" DC币",
                                                  u"§c超出剩余收购额度，仅能售出§e" + str(priceQueryList[12]) + u"个" if priceQueryList[4] else u"§a可出售"))
        if self.itemToSellNumber >= 10:
            selectGUI.setItem(3, initializeItemStack(Material.GOLD_INGOT, u"§a出售10个", "", u"§f预计总价：" + str(priceQueryList[1]) + u" DC币",
                                                    u"§f对应单价：" + str(priceQueryList[9]) + u" DC币",
                                                    u"§c超出剩余收购额度，仅能售出§e" + str(priceQueryList[12]) + u"个" if priceQueryList[5] else u"§a可出售"))
        else:
            spawnSeparators(selectGUI, 3, 3) # 挡板
        if self.itemToSellNumber >= 64:
            selectGUI.setItem(4, initializeItemStack(Material.GOLD_BLOCK, u"§a出售64个", "", u"§f预计总价：" + str(priceQueryList[2]) + u" DC币",
                                                    u"§f对应单价：" + str(priceQueryList[10]) + u" DC币",
                                                    u"§c超出剩余收购额度，仅能售出§e" + str(priceQueryList[12]) + u"个" if priceQueryList[6] else u"§a可出售"))
        else:
            spawnSeparators(selectGUI, 4, 4) # 挡板
        selectGUI.setItem(5, initializeItemStack(Material.BARREL, u"§a出售背包内全部（§b" + str(self.itemToSellNumber) + u"个§a）",
                                                  "", u"§f预计总价：" + str(priceQueryList[3]) + u" DC币", u"§f对应单价：" + str(priceQueryList[11]) + u" DC币",
                                                  u"§c超出剩余收购额度，仅能售出§e" + str(priceQueryList[12]) + u"个" if priceQueryList[7] else u"§a可出售"))
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
        elif clickInt == 3 and self.itemToSellNumber >= 10:
            temp_itemNum[self.player.getName()] = 10
            calculate().sellOut(player=self.player, itemToSell=self.itemToSell)
            self.player.closeInventory()
        elif clickInt == 4 and self.itemToSellNumber >= 64:
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
            historyDetail.set(str(sectionName), NewCycleProcess().residueRenew(Bukkit.getServer().getOfflinePlayer(playerName)))
    
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
            player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 价格环境指数较昨日相比&c减少" + str(deltaIndex)[1:] + u"&a！"))
        else:
            player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 价格环境指数较昨日未发生变化！"))
    else:
        player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 今日价格环境指数已经更新！当前指数为&b" + str(Decimal(Config.get('todayIndexEnvi')).quantize(Decimal('0.000'))) + u"&a！"))
    
    return True


def indexEnviQuery(sender, label, args):
    "价格环境指数查询函数"
    Config = ps.config.loadConfig('acquisition/parameterConfig.yml')
    player = sender.getPlayer()
    player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 今日价格环境指数为&b" + str(Decimal(Config.get('todayIndexEnvi')).quantize(Decimal('0.000'))) + u"&a！"))
    
    return True


def residueQuery(sender, label, args):
    "剩余收购额度查询函数"
    player = sender.getPlayer()
    historyDetail = ps.config.loadConfig('acquisition/historyDetail.yml')
    historyDetailSection = historyDetail.getConfigurationSection(str(player.getName()))
    tempDict = historyDetailSection.getValues(True)
    residue = Decimal(str(tempDict["RESIDUE"]))
    player.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 您本周期剩余收购额度为&b" + str(residue.quantize(Decimal('0.00'))) + u" DC币&a！"))
    
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


def residueChange(sender, label, args):
    "前台更改收购余额函数"
    changer = sender.getPlayer()
    player = Bukkit.getServer().getOfflinePlayer(str(args[0]))
    historyDetail = ps.config.loadConfig('acquisition/historyDetail.yml')
    historyDetailSection = historyDetail.getConfigurationSection(str(player.getName()))
    tempDict = historyDetailSection.getValues(True)
    residue = Decimal(float(tempDict["RESIDUE"]) + float(args[1])).quantize(Decimal('0.00'))
    historyDetail.set(str(args[0])+".RESIDUE", residue)
    historyDetail.save()

    if float(args[1]) >= 0:
        changer.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 已为&b" + str(args[0]) + u"&a增加&b" + str(Decimal(args[1]).quantize(Decimal('0.00')))
                                                                  + u" DC币&a收购额度，目前收购额度为&b" + str(residue) + u" DC币&a！"))
    else:
        changer.sendMessage(ChatColor.translateAlternateColorCodes('&', u"&e[DC收购]&a 已为&b" + str(args[0]) + u"&a减少&b" + str(Decimal(args[1]).quantize(Decimal('0.00')))[1:]
                                                                  + u" DC币&a收购额度，目前收购额度为&b" + str(residue) + u" DC币&a！"))

    return True


def start():
    "开服执行函数"
    def indexEnviUpdateStart():
        "价格环境指数更新函数（开服时执行）"
        Config = ps.config.loadConfig('acquisition/parameterConfig.yml')
        today = Config.get('today')

        if today != date.today().strftime("%Y-%m-%d"):
            todayIndex = Decimal(NewCycleProcess().indexEnvi(int(datetime.strptime(today, '%Y-%m-%d').strftime('%j')))).quantize(Decimal('0.000'), rounding=ROUND_DOWN)

            Config.set('todayIndexEnvi', todayIndex)
            Config.set('today', str(date.today()))
            Config.save()

        return True
    
    def newCycleStart():
        "新周期执行函数（开服时执行）"
        Config = ps.config.loadConfig('acquisition/parameterConfig.yml')
        cycleNow = Config.get('cycleNow')

        if cycleNow != date.today().strftime("%Y-%m-%d"):
            historyDetail = ps.config.loadConfig('acquisition/historyDetail.yml')
            historyDetailDict = historyDetail.getValues(True)
            historyMoney = ps.config.loadConfig('acquisition/historyMoney.yml')
            historyMoneyDict = historyMoney.getValues(True)

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
                    historyDetail.set(str(sectionName), NewCycleProcess().residueRenew(Bukkit.getServer().getOfflinePlayer(playerName)))
        
            historyDetail.save()
            Config.set("cycleNow", str(date.today()))
            Config.save()
            if str(date.today()) not in historyMoneyDict.keys():
                historyMoney.createSection(str(date.today()))
            historyMoney.save()

        return True

    indexEnviUpdateStart()
    current_day = datetime.now()
    if current_day.weekday() == 0:  # 每周一进入新周期
        newCycleStart()


def stop():
    "关闭所有打开菜单的玩家"
    closeGuiForAll("acq.")


ps.command.registerCommand(main, "acquisition")
ps.command.registerCommand(newCycle, "newcycle")
ps.command.registerCommand(indexEnviUpdate, "newday")
ps.command.registerCommand(indexEnviQuery, "acqindexenvi")
ps.command.registerCommand(residueQuery, "acqresidue")
ps.command.registerCommand(residueChange, "acqresiduechange")
ps.listener.registerListener(onGUIOpen, InventoryClickEvent, True)
