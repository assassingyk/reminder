# reminder
适用hoshino的自定义定时提醒插件

~~依然是竹竹重制计划的一部分（）~~

实现思路上参考了[@zyujs](https://github.com/zyujs)大佬的[pcr_calendar](https://github.com/zyujs/pcr_calendar)里关于定时推送的思路

使用方式上参考隔壁 [@Tsuk1ko](https://github.com/Tsuk1ko) 大佬家的[竹竹](https://github.com/Tsuk1ko/cq-picsearcher-bot)的定时提醒功能，具体指令格式因为也没想到更自然(?)的方式所以也没换，基本用法可以直接参考那边的[wiki](https://github.com/Tsuk1ko/cq-picsearcher-bot/wiki/%E9%99%84%E5%8A%A0%E5%8A%9F%E8%83%BD#%E5%AE%9A%E6%97%B6%E6%8F%90%E9%86%92)

## 指令列表

指令私聊群聊通用。单群或单人可设置的提醒数量可分别设置。

- `--time=(cron表达式) --rmd=(提醒内容)` 设置定时提醒。时间表达式为cron格式，空格与`;`分隔均可，以防刷屏不允许使用分钟级corn表达式，如有需要可自行注释相关内容；
- `--rmd-list` 查看当前群聊/私聊定时提醒列表及其id；
- `--rmd-del=(提醒ID)` 删除对应id定时提醒；
