"""Schema knowledge for ThinkingData projects - used by AI to generate correct SQL."""

# 项目映射
PROJECTS = {
    "102": "黄老师",
    "105": "丁老师",
    "116": "魏老师",
    "128": "支付中心",
}

# 用户表核心字段（所有项目通用）
USER_TABLE_SCHEMA = """
用户表 v_user_{appid} 核心字段：
- "#user_id": 用户ID (string)
- "#account_id": 账号ID (string)
- "register_time": 注册时间 (timestamp)
- "bundle_id": 包名 (string)
- "link": 注册时链接 (string)
- "af_id": AFID (string)
- "first_app_start_time": 首次进入loading时间 (timestamp)
- "last_app_start_time": 最近启动时间 (timestamp)
- "client_version": 客户端版本号 (string)
- "first_pay_time": 首次充值时间 (timestamp)
- "second_pay_time": 第二次充值时间 (timestamp)
- "first_money_game_time": 首次开始现金局时间 (timestamp)
- "role_name": 当前角色名 (string)
- "phone_number": 手机号 (string)
- "redeem_email": 打款邮箱 (string)
- "user_status": 用户状态 (string) - 0:正常, 1:封号, 2:冻结
- "email": 邮箱 (string)
- "deposit_times_sum": 累计充值次数 (number)
- "deposit_amount_sum": 累计充值金额 (number)
- "game_sum": 总对局数 (number)
- "money_game_sum": 累积真金SPIN次数 (number)
- "bonus_game_sum": 累积BonusSPIN次数 (number)
- "chips_game_sum": 累积金币SPIN次数 (number)
- "withdraw_times_sum": 累计提现次数 (number)
- "withdraw_amount_sum": 累计提现金额 (number)
- "withdraw_amount_success_sum": 累计成功提现金额 (number)
- "bet_money_sum": 累积下注bonus和money (number)
- "win_money_sum": 累计赢得money (number)
- "win_chips_sum": 累计赢得金币 (number)
- "money_bet_max": 最高下注额度 (number)
- "money_win_max": 最高赢取金额 (number)
- "money_multiple_max": 最高赢取倍数 (number)
- "money_rtp_sum": 真金场总返奖率 (number)
- "coin_rtp_sum": 金币场总返奖率 (number)
- "current_level": 当前角色等级 (number)
- "current_money": 当前全部美金 (number)
- "current_bonus": 当前赠送美金 (number)
- "current_chips": 当前金币数 (number)
- "vip_level": 当前VIP等级 (number)
- "ads_times_sum": 观看广告次数 (number)
- "is_organic": 是否自然量 (number) - 0=非自然量, 1=自然量
- "withdraw_pay_rate": 生涯提现比 (number) - 累计成功提现/累计充值
- "kyc_status": KYC状态 (string) - basic/enhanced/not-passed/null
- "last_withdraw_apply_time": 最近一次申请提现时间 (timestamp)
- "last_withdraw_gmv": 上次提现至今的总GMV (number)
- "last_withdraw_pay_amount": 上次提现至今的总成功充值金额 (number)
- "pay_bonus_amount_sum": 充值赠送的bonus总额 (number)
- "other_bonus_amount_sum": 非充值赠送的bonus总额 (number)
- "most_played_machine": 玩最多的机台 (string)
- "gender": 用户性别 (string) - F/M
- "birthday": 玩家生日 (string)
"""

# 事件表核心字段
EVENT_TABLE_SCHEMA = """
事件表 v_event_{appid} 系统字段（固定写法，不可更改）：

【系统必传字段 - 每条SQL查询事件表时必须包含】
- "$part_date": 分区日期 (varchar, 格式'YYYY-MM-DD') ⚠️ 必传！WHERE条件必须包含此字段！
- "#event_name": 事件名称 (string) - 用于过滤具体事件类型，如 WHERE "#event_name" = 'order_pay'
- "#event_time": 事件发生时间 (timestamp) - 精确到毫秒的事件时间戳

【系统通用字段】
- "#user_id": 用户ID (string)
- "#account_id": 账号ID (string)
- "#country": 国家 (string)
- "#province": 省份 (string)
- "#city": 城市 (string)
- "#os": 操作系统 (string)
- "#device_model": 设备型号 (string)
- "#ip": IP地址 (string)

⚠️ 重要提醒：
1. "$part_date" 是分区字段，查询事件表时 WHERE 中必须包含，否则查询会报错！
2. "#event_name" 用于区分不同事件类型
3. "#event_time" 是事件精确时间，如需按时间排序用这个字段
4. 时间范围过滤用 "$part_date"，精确时间排序用 "#event_time"

重要事件列表及属性：

【充值相关】
- "order_pay": 订单支付成功
  - "pay_id": 订单ID
  - "charge_id": 充值项ID
  - "payment_type": 支付方式 (Card/Apple Pay/PayPal/Checkout/Rapyd)
  - "pay_enter_name": 订单入口 (main_page/private/machine/welcome)
  - "pay_amount": 付款金额
  - "pay_bonus": 赠送金额
  - "net_amount": 商户实际到账金额
  - "service_charge": 手续费
  - "is_first_pay": 是否首充
  - "is_true": 是否成功 (boolean)
  - "bankroll_money": 用户持有money
  - "bankroll_bonus": 用户持有bonus
  - "card_bin": 卡号前6位
  - "ip": IP地址
  - "ip_info": IP解析地址(object: country/province/city)

- "order_pay_fail": 订单支付失败
  - "pay_id": 订单ID
  - "pay_center_status": 支付中心订单状态
  - "is_true": 是否成功
  - "card_bin": 卡号前6位

- "order_pay_bad": 订单支付坏账
  - 同order_pay字段

- "pay_dispute": 产生争议
  - "pay_id": 订单ID
  - "pay_amount": 付款金额
  - "deposit_times_sum": 累计充值次数
  - "deposit_amount_sum": 累计充值金额

【提现相关】
- "withdraw_apply": 提现申请
  - "withdraw_id": 提现订单ID
  - "amount": 提现金额
  - "bankroll_money": 用户持真金
  - "bankroll_bonus": 用户持奖励金
  - "deposit_amount_sum": 累计充值金额
  - "deposit_amount_24": 提现前24h充值金额
  - "rtp_24": 提现前24h内真金场rtp
  - "withdraw_fee": 手续费
  - "payment_method": 打款方式 (paypal/bank card/refund)
  - "is_first_withdraw": 是否首次提现
  - "ip": IP地址

- "withdraw_success": 提现成功
  - "withdraw_id": 提现订单ID
  - "amount": 提现金额
  - "withdraw_fee": 手续费
  - "is_first_withdraw": 是否首次提现
  - "is_quick_withdraw": 是否快速打款
  - "payment_method": 打款方式
  - "payment_time": 打款时间

- "withdraw_cancel": 提现取消（银行返回失败）
  - "withdraw_id": 提现订单ID
  - "amount": 提现金额
  - "payment_method": 打款方式

- "withdraw_failure": 打款失败
  - "withdraw_id": 提现订单ID
  - "amount": 提现金额
  - "freeze_amount": 冻结金额

- "withdraw_verify": 提现审核
  - "withdraw_id": 提现订单ID
  - "amount": 提现金额
  - "verify_result": 审核结果 (1待审核/2审核中/3打款成功/4打款失败/5用户取消/6冻结拉黑/103审核成功/105可疑)
  - "is_final": 是否最终状态

【游戏相关】
- "game_play": 游戏过程(SPIN)
  - "spin_id": spinID
  - "machine_id": 机台ID
  - "provider_name": 供应商名称
  - "machine_type": 机台类型 (1:sc, 2:ga)
  - "bankroll_money": 用户持金-money
  - "bankroll_bonus": 用户持金-bonus
  - "bankroll_chips": 用户持金-chips
  - "bet_money": 下注额度-money
  - "bet_bonus": 下注额度-bonus
  - "bet_chips": 下注额度-chips
  - "spin_type": spin类型 (1:normal, 2:free_game)
  - "win_amount": 返奖额度
  - "winrate": 赢奖比例 (win/bet)
  - "is_auto": 是否自动spin
  - "is_jackpot": 是否得到Jackpot
  - "jackpot_type": Jackpot类型 (Mini/Minor/Major/Grand/Super)
  - "cused": 触发条件 (C11正常/C21新人/C31货币过多/C51充值后/C71快输光/C81回归)
  - "rused": 数值结果

- "game_start": 游戏开始（进入机台）
  - "machine_id": 机台ID
  - "provider_name": 供应商名称
  - "machine_type": 机台类型

- "game_result": 用户离开机台
  - "machine_id": 机台ID
  - "total_spin_money": 一整局下注money和
  - "total_spin_bonus": 一整局下注bonus和
  - "total_win_amount": 一整局赢的和
  - "sc_spin_number": SC spin次数
  - "gc_spin_number": GC spin次数

【货币变化】
- "currency_change": 货币变化
  - "source_type": 来源类型 (1:machine/2:pay/3:withdraw/4:checkin/5:online_reward/6:level_up/7:storage/8:ads_roulette/9:ads_rewards/11:sc_roulette/12:sc_lottery/13:starterpack/14:luckyflip/15:subscription/16:bank/17:protection/18:inbox/19:jackpot)
  - "source_id": 来源ID
  - "money_previous": 变化前money
  - "money_change": money变化数量(正负)
  - "bonus_previous": 变化前bonus
  - "bonus_change": bonus变化数量(正负)
  - "chips_previous": 变化前chips
  - "chips_change": chips变化数量(正负)

【SC游戏中心】
- "sc_roulette_play": SC转盘过程
  - "bankroll_money", "bankroll_bonus", "bet_money", "bet_bonus", "win_amount"
- "sc_lottery_play": SC刮卡过程
  - "bankroll_money", "bankroll_bonus", "bet_money", "bet_bonus", "win_amount"

【KYC验证】
- "kyc_begin": 触发KYC验证
  - "kyc_reason": 触发原因 (1提现/2SC游戏/3充值前/4充值后)
  - "kyc_level": 验证等级
- "kyc_end": KYC验证结束
  - "is_success": 验证状态
  - "fail_reason": 失败原因

【Geo-comply】
- "geocomply_result": geocomply返回结果
  - "is_pass": 是否通过
  - "gps_country_code": GPS国家代码
  - "error_message": 不通过原因
  - "launch_reason": 发起原因 (0定时检查/1登录/2SC游戏/3Spin/4充值/5提现)
"""

# 风控常用查询模板
RISK_QUERY_TEMPLATES = """
风控常用查询场景：
1. 查询用户充值：事件 "order_pay" 且 "is_true" = true
2. 查询用户提现：事件 "withdraw_apply" (申请) / "withdraw_success" (成功)
3. 查询用户游玩：事件 "game_play"
4. 查询用户RTP：用户表 "money_rtp_sum" 字段，或通过 game_play 计算 SUM(win_amount)/SUM(bet_money+bet_bonus)
5. 查询坏账/争议：事件 "order_pay_bad" 或 "pay_dispute"
6. 查询封号用户：用户表 "user_status" = '1'
7. 查询提现审核：事件 "withdraw_verify"，verify_result字段
8. 查询大额赢家：game_play 中 win_amount 排序
9. 查询Jackpot中奖：game_play 中 "is_jackpot" = true
"""
