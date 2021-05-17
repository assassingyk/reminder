import hoshino
import nonebot
import os
import re
import json

from traceback import format_exc
from asyncio import Lock, sleep
from croniter import croniter
from datetime import datetime

sv_help = '''
自定义定时提醒功能，私聊群聊均可使用
[--time=(cron表达式) --rmd=(提醒内容)] 设置定时提醒。时间表达式不允许使用分钟级
[--rmd-list] 查看当前群聊/私聊定时提醒列表及其id
[--rmd-del=(提醒ID)] 删除对应id定时提醒
'''.strip()

PERSONAL_LIMIT = 5
GROUP_LIMIT = 10

sv = hoshino.Service('reminder', help_=sv_help)

group_data = {}
private_data = {}
curent_gid = 0
curent_pid = 0
lckg = Lock()
lckp = Lock()


def load_data(file):
    path = os.path.join(os.path.dirname(__file__), file)
    if not os.path.exists(path):
        print('path not exist!')
        return
    try:
        with open(path, encoding='utf8') as f:
            data = json.load(f)
            return data
    except:
        print(format_exc())


def save_data(var, file):
    path = os.path.join(os.path.dirname(__file__), file)
    if not os.path.exists(path):
        print('path not exist!')
        return
    try:
        with open(path, 'w', encoding='utf8') as f:
            json.dump(var, f, ensure_ascii=False, indent=2)
    except:
        print(format_exc())


@nonebot.on_startup
async def startup():
    print(f"start rmd config reading")
    global group_data, private_data, curent_gid, curent_pid

    group = load_data('gdata.json')
    private = load_data('pdata.json')

    group_data = group['group_data']
    curent_gid = int(group['curent_gid'])

    private_data = private['private_data']
    curent_pid = int(private['curent_pid'])

    for rmd_id in group_data:
        try:
            update_group_reminder(rmd_id)
        except:
            print(f"error updating id {rmd_id}")
            print(format_exc())
            pass
    for rmd_id in private_data:
        try:
            update_private_reminder(rmd_id)
        except:
            print(f"error updating id {rmd_id}")
            print(format_exc())
            pass


async def send_group_reminder(group_id, msg):
    bot = hoshino.get_bot()
    available_group = await sv.get_enable_groups()
    if int(group_id) not in available_group:
        return
    for _ in range(5):  # 失败重试5次
        try:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
            sv.logger.info(f'群{group_id}推送定时提醒成功')
            break
        except:
            print(format_exc())
            sv.logger.info(f'群{group_id}推送定时提醒失败')
        await sleep(60)


async def send_private_reminder(user_id, group_id, msg):
    bot = hoshino.get_bot()
    available_group = await sv.get_enable_groups()
    if group_id and int(group_id) not in available_group:
        return
    for _ in range(5):  # 失败重试5次
        try:
            await bot.send_private_msg(user_id=int(user_id), group_id=int(group_id), message=msg)
            sv.logger.info(f'用户{user_id}推送定时提醒成功')
            break
        except:
            print(format_exc())
            sv.logger.info(f'用户{user_id}推送定时提醒失败')
        await sleep(60)


def update_group_reminder(rmd_id):
    rmd_id = str(rmd_id)
    if rmd_id not in group_data:
        return
    group_id = group_data[rmd_id]['group']

    nonebot.scheduler.add_job(
        send_group_reminder,
        'cron',
        args=(group_id, group_data[rmd_id]['msg']),
        id=f'reminder_group_{rmd_id}',
        replace_existing=True,
        day_of_week=group_data[rmd_id]['day_of_week'],
        month=group_data[rmd_id]['month'],
        day=group_data[rmd_id]['day'],
        hour=group_data[rmd_id]['hour'],
        minute=group_data[rmd_id]['minute']
    )
    print(f"updated grmd id {rmd_id}")


def update_private_reminder(rmd_id):
    rmd_id = str(rmd_id)
    if rmd_id not in private_data:
        return
    user_id = private_data[rmd_id]['user']
    group_id = private_data[rmd_id]['group']

    nonebot.scheduler.add_job(
        send_private_reminder,
        'cron',
        args=(user_id, group_id, private_data[rmd_id]['msg']),
        id=f'reminder_private_{rmd_id}',
        replace_existing=True,
        day_of_week=private_data[rmd_id]['day_of_week'],
        month=private_data[rmd_id]['month'],
        day=private_data[rmd_id]['day'],
        hour=private_data[rmd_id]['hour'],
        minute=private_data[rmd_id]['minute']
    )
    print(f"updated prmd id {rmd_id}")


def checkcron(cron):
    legal = ['1', '2', '3', '4', '5', '6', '7', '8', '9',
             '0', ' ', ';', ',', '-', '*', '?', '/', 'L', 'C', '#']
    flag = 0
    for letter in cron:
        if letter not in legal:
            return None
    if ';' in cron:
        cron = cron.replace(';', ' ')
    cronlist = cron.split(' ')
    if len(cronlist) != 5:
        if len(cronlist) == 6:
            return cronlist[-5:]
        else:
            return None
    return cronlist


@sv.on_rex(r'^--time=(.*?)--rmd=(.*)')
async def start_reminder(bot, ev):
    global group_data, curent_gid, lckg
    group_id = str(ev['group_id'])
    user_id = str(ev['user_id'])
    try:
        if not hoshino.priv.check_priv(ev, hoshino.priv.ADMIN):
            await bot.send(ev, '定时提醒设置需管理及以上权限~')
            return
        count = 0
        for rmd_id in group_data:
            if group_data[rmd_id]['group'] == str(group_id):
                count += 1
        if count >= GROUP_LIMIT:
            await bot.send(ev, f'为防滥用每群仅能设置{GROUP_LIMIT}条定时提醒~')
            return
        msg = str(re.match('^--time=(.*?)--rmd=(.*)',
                  ev['raw_message']).group(2).strip())
        print(msg)
        cron = str(re.match('^--time=(.*?)--rmd=(.*)',
                   ev['raw_message']).group(1).strip())
        print(cron)
        time = checkcron(cron)
        if not time:
            await bot.send(ev, 'cron表达式不合法，请重新输入~')
            return
        if '*' in time[0] or '/' in time[0] or '-' in time[0]:
            await bot.send(ev, '为防刷屏不允许使用分钟级cron表达式，请重新输入~')
            return
        async with lckg:
            curent_gid = curent_gid + 1
            group_data[str(curent_gid)] = {
                'group': str(group_id),
                'user': str(user_id),
                'msg': msg,
                'day_of_week': time[4],
                'month': time[3],
                'day': time[2],
                'hour': time[1],
                'minute': time[0],
            }
            update_group_reminder(str(curent_gid))
            group = {'group_data': group_data, 'curent_gid': curent_gid}
            save_data(group, 'gdata.json')

        str_time_now = datetime.now()
        iter = croniter(' '.join(time), str_time_now)
        next = str(iter.get_next(datetime))
        await bot.send(ev, f'已添加定时提醒！下次触发时间：{next}, 提醒内容：{msg}')
    except Exception as e:
        print(format_exc())
        await bot.send(ev, f'错误：{e}')


@sv.on_fullmatch('--rmd-list')
async def list_reminder(bot, ev):
    global group_data, curent_gid, lckg
    group_id = str(ev['group_id'])
    user_id = str(ev['group_id'])
    try:
        if not hoshino.priv.check_priv(ev, hoshino.priv.ADMIN):
            await bot.send(ev, '定时提醒设置需管理及以上权限~')
            return
        reply = []
        async with lckg:
            for rmd in group_data:
                if group_data[rmd]['group'] == str(group_id):
                    time = f"{group_data[rmd]['minute']} {group_data[rmd]['hour']} {group_data[rmd]['day']} {group_data[rmd]['month']} {group_data[rmd]['day_of_week']}"
                    reply.append(
                        f"id={rmd}，提醒时间：{time}，提醒内容：{group_data[rmd]['msg']}")
        reply = '\n'.join(reply)
        if reply:
            await bot.send(ev, f"本群当前定时提醒：\n{reply}")
        else:
            await bot.send(ev, f"本群当前无定时提醒！")
    except Exception as e:
        print(format_exc())
        await bot.send(ev, f'错误：{e}')


@sv.on_rex(r'^--rmd-del=(.*)')
async def del_reminder(bot, ev):
    global group_data, curent_gid, lckg
    group_id = str(ev['group_id'])
    user_id = str(ev['group_id'])
    try:
        if not hoshino.priv.check_priv(ev, hoshino.priv.ADMIN):
            await bot.send(ev, '定时提醒设置需管理及以上权限~')
            return
        rmd_id = str(ev['match'].group(1).strip())
        if not rmd_id.isdigit:
            await bot.send(ev, 'id格式有误，请重新输入……')
            return
        if rmd_id not in group_data:
            await bot.send(ev, '未找到该id……')
            return
        if group_data[rmd_id]['group'] != str(group_id):
            await bot.send(ev, '不可删除非本群提醒……')
            return
        async with lckg:
            nonebot.scheduler.remove_job(f'reminder_group_{rmd_id}')
            group_data.pop(rmd_id)
            group = {'group_data': group_data, 'curent_gid': curent_gid}
            save_data(group, 'gdata.json')
        await bot.send(ev, f'定时提醒{rmd_id}已移除~')
    except Exception as e:
        print(format_exc())
        await bot.send(ev, f'错误：{e}')

bot = nonebot.get_bot()


@bot.on_message('private')
async def picprivite(ctx):
    global private_data, curent_pid, lckp
    type = ctx["sub_type"]
    user_id = int(ctx["sender"]["user_id"])
    group_id = 0
    if type == "group":
        group_id = int(ctx["sender"]["group_id"])

    if re.match(r"^--rmd-del=(.*)", str(ctx['message'])):
        try:
            rmd_id = re.match("^--rmd-del=(.*)",
                              str(ctx['message'])).group(1).strip()
            if not rmd_id.isdigit:
                await bot.send_private_msg(user_id=int(user_id), group_id=int(group_id), message='id格式有误，请重新输入……')
                return
            if rmd_id not in private_data:
                await bot.send_private_msg(user_id=int(user_id), group_id=int(group_id), message='未找到该id……')
                return
            if private_data[rmd_id]['user'] != str(user_id):
                await bot.send_private_msg(user_id=int(user_id), group_id=int(group_id), message='不可删除非本人提醒……')
                return
            async with lckp:
                nonebot.scheduler.remove_job(f'reminder_private_{rmd_id}')
                private_data.pop(rmd_id)
                private = {'private_data': private_data,
                           'curent_pid': curent_pid}
                save_data(private, 'pdata.json')
            await bot.send_private_msg(user_id=int(user_id), group_id=int(group_id), message=f'定时提醒{rmd_id}已移除~')
        except Exception as e:
            print(format_exc())
            await bot.send_private_msg(user_id=int(user_id), group_id=int(group_id), message=f'错误：{e}')
        return

    elif re.match('^rmd=(.*?)time=(.*)', str(ctx['message'])):
        try:
            count = 0
            for rmd_id in private_data:
                if private_data[rmd_id]['user'] == str(user_id):
                    count += 1
            if count >= PERSONAL_LIMIT:
                await bot.send_private_msg(user_id=int(user_id), group_id=int(group_id), message=f'为防止滥用每人仅能设置{PERSONAL_LIMIT}条私聊定时提醒~')
            msg = re.match('^rmd=(.*?)time=(.*)',
                           str(ctx['message'])).group(1).strip()
            cron = re.match('^rmd=(.*?)time=(.*)',
                            str(ctx['message'])).group(2).strip()
            time = checkcron(cron)
            if not time:
                await bot.send_private_msg(user_id=int(user_id), group_id=int(group_id), message='cron表达式不合法，请重新输入~')
                return
            if '*' in time[0] or '/' in time[0] or '-' in time[0]:
                await bot.send_private_msg(user_id=int(user_id), group_id=int(group_id), message='为防刷屏不允许使用分钟级cron表达式，请重新输入~')
                return
            async with lckp:
                curent_pid = curent_pid + 1
                private_data[str(curent_pid)] = {
                    'group': str(group_id),
                    'user': str(user_id),
                    'msg': msg,
                    'day_of_week': time[4],
                    'month': time[3],
                    'day': time[2],
                    'hour': time[1],
                    'minute': time[0],
                }
                update_private_reminder(str(curent_pid))
                private = {'private_data': private_data,
                           'curent_pid': curent_pid}
                save_data(private, 'pdata.json')
            str_time_now = datetime.now()
            iter = croniter(' '.join(time), str_time_now)
            next = str(iter.get_next(datetime))
            await bot.send_private_msg(user_id=int(user_id), group_id=int(group_id), message=f'已添加定时提醒！下次触发时间：{next}, 提醒内容：{msg}')
        except Exception as e:
            print(format_exc())
            await bot.send_private_msg(user_id=int(user_id), group_id=int(group_id), message=f'错误：{e}')
        return

    elif str(ctx['message']) == '--rmd-list':
        try:
            reply = []
            async with lckp:
                for rmd in private_data:
                    if private_data[rmd]['user'] == str(user_id):
                        time = f"{private_data[rmd]['minute']} {private_data[rmd]['hour']} {private_data[rmd]['day']} {private_data[rmd]['month']} {private_data[rmd]['day_of_week']}"
                        reply.append(
                            f"id={rmd},时间：{time},内容：{private_data[rmd]['msg']}")
            reply = '\n'.join(reply)
            if reply:
                await bot.send_private_msg(user_id=int(user_id), group_id=int(group_id), message=f"您当前定时提醒：\n{reply}")
            else:
                await bot.send_private_msg(user_id=int(user_id), group_id=int(group_id), message=f"您当前无定时提醒！")
        except Exception as e:
            print(format_exc())
            await bot.send_private_msg(user_id=int(user_id), group_id=int(group_id), message=f'错误：{e}')
        return

    else:
        return
