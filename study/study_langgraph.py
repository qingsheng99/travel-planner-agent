"""
================================================================================
          LangGraph 状态机学习指南 —— 基于 Travel Planner 项目实战
================================================================================

LangGraph 是 LangChain 推出的"有向图"框架，用于构建多步骤的 AI 智能体。
它让 LLM 不再是"一问一答"，而是可以"边思考边调用工具，再思考再调用..."

项目中的旅行规划助手就是典型的 LangGraph 应用：
    用户提问 → 意图识别 → 查天气/查航班/查酒店/查景点 → 生成行程

运行方式：
    pip install langgraph langchain langchain-openai
    python study/study_langgraph.py

注意：如果不配置 OpenAI API Key，部分演示会用模拟数据跑通流程。
"""

import os
import json
from typing import TypedDict, Annotated, List, Dict, Optional, Literal
import operator


# ============================================================================
#   Part 0: 前置知识 —— 什么是状态机？
# ============================================================================
#
# 状态机 = 状态（State）+ 转移（Transition）
#
# 传统程序：线性执行 A → B → C → D
# 状态机：  可以根据"当前状态"决定"下一步去哪"，支持分支和循环
#
# 想象一个旅行规划流程：
#   用户说"我想去北京玩3天"
#     ↓
#   [意图识别] → 判断用户想要什么
#     ├─ 查天气 → [查天气] → 回到[意图识别]
#     ├─ 查航班 → [查航班] → 回到[意图识别]
#     ├─ 查酒店 → [查酒店] → 回到[意图识别]
#     ├─ 查景点 → [查景点+查知识库] → 回到[意图识别]
#     └─ 生成行程 → [生成行程] → 结束
#
# LangGraph 就是帮我们实现这种"有向图"流程的框架。


# ============================================================================
#   Part 1: 最简状态机 —— 先理解核心概念
# ============================================================================
#
# LangGraph 的核心概念只有 3 个：
#   1. State（状态）：整个流程共享的数据，像"黑板"一样，所有节点都能读写
#   2. Node（节点）：一个处理步骤，输入 State，输出 State 的更新
#   3. Edge（边）：节点之间的连接，决定执行顺序

# ── 1.1 定义 State ─────────────────────────────────────────────────────────
# 项目中的 State 定义在 graph/state.py

class SimpleState(TypedDict):
    """
    最简单的状态定义
    
    TypedDict 是 Python 的"类型化字典"：
    - 像普通 dict 一样用 state["key"] 访问
    - 但有类型提示，IDE 能自动补全
    
    项目中的 TravelState 就是这样定义的，有十几个字段。
    """
    messages: list           # 对话历史
    count: int               # 一个计数器
    result: Optional[str]    # 最终结果


# ── 1.2 定义节点 ────────────────────────────────────────────────────────────
# 节点就是函数，输入 State，返回 State 的更新（部分字段）

def node_a(state: SimpleState) -> SimpleState:
    """节点 A：加一条消息，计数器 +1"""
    print(f"  [Node A] 执行中... 当前 count={state['count']}")
    return {
        "messages": state["messages"] + ["A 处理过了"],
        "count": state["count"] + 1,
    }


def node_b(state: SimpleState) -> SimpleState:
    """节点 B：加一条消息，计数器 +1"""
    print(f"  [Node B] 执行中... 当前 count={state['count']}")
    return {
        "messages": state["messages"] + ["B 处理过了"],
        "count": state["count"] + 1,
    }


def node_c(state: SimpleState) -> SimpleState:
    """节点 C：最终节点，写结果"""
    print(f"  [Node C] 执行中... 当前 count={state['count']}")
    return {
        "messages": state["messages"] + ["C 处理完了"],
        "result": f"完成！共处理了 {state['count'] + 1} 步",
    }


# ── 1.3 定义路由器（条件边） ────────────────────────────────────────────────
# 路由器决定"下一步去哪"。它根据当前状态，返回下一个节点的名字。

def router(state: SimpleState) -> Literal["node_b", "node_c"]:
    """
    条件路由器：根据 count 的值决定走哪条路
    
    返回值必须是节点名称，LangGraph 根据返回值找到对应的节点。
    项目中的 supervisor 也是类似的逻辑。
    """
    if state["count"] < 2:
        print(f"  [Router] count={state['count']} < 2，去 node_b")
        return "node_b"
    else:
        print(f"  [Router] count={state['count']} >= 2，去 node_c（结束）")
        return "node_c"


# ── 1.4 组装成图 ────────────────────────────────────────────────────────────
# 把节点和边连起来，编译成可执行图

def build_simple_graph():
    """
    构建最简状态机
    
    图结构：
        node_a → router → node_b → router（循环）
                        → node_c → END
    """
    from langgraph.graph import StateGraph, END

    # Step 1: 创建图，指定 State 类型
    workflow = StateGraph(SimpleState)

    # Step 2: 添加节点
    workflow.add_node("node_a", node_a)     # 参数：(节点名, 处理函数)
    workflow.add_node("node_b", node_b)
    workflow.add_node("node_c", node_c)

    # Step 3: 设置入口节点
    workflow.set_entry_point("node_a")      # 从这里开始执行

    # Step 4: 添加条件边（从 node_a 出来后，走 router 判断）
    workflow.add_conditional_edges(
        "node_a",           # 起点节点
        router,             # 路由器函数
        {                   # 路由器返回值 → 目标节点 的映射
            "node_b": "node_b",
            "node_c": "node_c",
        }
    )

    # Step 5: 添加条件边（从 node_b 出来后，也走 router 判断）
    workflow.add_conditional_edges(
        "node_b",
        router,
        {
            "node_b": "node_b",
            "node_c": "node_c",
        }
    )

    # Step 6: node_c 是终点，连到 END
    workflow.add_edge("node_c", END)

    # Step 7: 编译
    return workflow.compile()


def demo_simple_graph():
    """运行最简状态机"""
    print("\n" + "=" * 60)
    print("  [PART 1] 最简状态机")
    print("=" * 60)

    graph = build_simple_graph()

    # 初始状态
    initial_state = {
        "messages": [],
        "count": 0,
        "result": None,
    }
    print(f"\n  初始状态: {initial_state}")

    # 运行
    print(f"\n  开始执行...\n")
    result = graph.invoke(initial_state)

    print(f"\n  最终结果: {result}")
    print(f"  messages: {result['messages']}")
    print(f"  result: {result['result']}")


# ============================================================================
#   Part 2: 项目中的 State 定义（对应 graph/state.py）
# ============================================================================
#
# 项目中的 TravelState 比 SimpleState 复杂得多，但核心概念是一样的。

def demo_travel_state():
    """讲解项目中的 TravelState"""
    print("\n" + "=" * 60)
    print("  [PART 2] 项目中的 TravelState")
    print("=" * 60)

    print("""
    ┌────────────────────────────────────────────────────────────────┐
    │                   TravelState（项目中的状态）                    │
    ├────────────────────────────────────────────────────────────────┤
    │  messages: list     ← 对话历史（累加，不覆盖）                   │
    │  user_id: int       ← 当前用户 ID                              │
    │  trip_id: int       ← 当前行程 ID                              │
    │  destination: str   ← 目的地（如"北京"）                        │
    │  dates: dict        ← 日期范围                                 │
    │  budget: dict       ← 预算范围                                 │
    │  travelers: int     ← 出行人数                                 │
    │  preferences: dict  ← 用户偏好                                 │
    │  weather_info: dict ← 天气信息（查天气后填充）                   │
    │  flight_info: list  ← 航班信息（查航班后填充）                   │
    │  hotel_info: list   ← 酒店信息（查酒店后填充）                   │
    │  poi_info: list     ← 景点信息（查景点后填充）                   │
    │  itinerary: dict    ← 生成的行程（最终输出）                     │
    │  next: str          ← 下一步做什么（由路由器决定）               │
    └────────────────────────────────────────────────────────────────┘

    关键设计：messages 用 Annotated[list, operator.add]
    这意味着每次节点返回 messages 时，新的消息会追加到现有消息后面，
    而不是覆盖。这就是"多轮对话记忆"的实现方式。
    """)

    # 演示 operator.add 的累加效果
    print("  ▶ messages 的累加机制演示:")
    msgs = ["你好"]
    print(f"    初始: {msgs}")

    # 节点 A 返回  {"messages": ["A说查天气"]}
    # 实际效果：msgs + ["A说查天气"] = ["你好", "A说查天气"]
    msgs = msgs + ["A说查天气"]
    print(f"    节点A后: {msgs}")

    # 节点 B 返回  {"messages": ["B说天气晴"]}
    msgs = msgs + ["B说天气晴"]
    print(f"    节点B后: {msgs}")

    print(f"""
    项目中的定义：
        class TravelState(TypedDict):
            messages: Annotated[list, operator.add]
            # ↑ 这个 Annotated 告诉 LangGraph：
            #   "messages 字段的更新方式是累加，不是覆盖"


    对比普通字段：
        next: Optional[str]           # 普通字段，每次覆盖
        weather_info: Optional[Dict]  # 普通字段，每次覆盖
        messages: Annotated[list, operator.add]  # 累加字段
    """)


# ============================================================================
#   Part 3: 从简单到复杂 —— 旅行规划简化版
# ============================================================================
#
# 先不用 LangChain/LangGraph 库，用纯 Python 理解"意图识别+工具调用"的流程

# ── 3.1 模拟 LLM 和工具 ────────────────────────────────────────────────────

def mock_llm_classify(message: str) -> str:
    """
    模拟 LLM 的意图分类

    项目中的真实代码（graph/nodes.py）：
        response = llm.invoke(messages)
        next_step = response.content.strip().lower()
        
    这里用关键词匹配模拟 LLM 行为。
    """
    msg = message.lower()
    if any(k in msg for k in ["天气", "温度", "下雨"]):
        return "weather"
    elif any(k in msg for k in ["航班", "飞机", "机票"]):
        return "flights"
    elif any(k in msg for k in ["酒店", "住宿", "住"]):
        return "hotels"
    elif any(k in msg for k in ["景点", "玩", "逛", "景点"]):
        return "pois"
    elif any(k in msg for k in ["行程", "计划", "安排", "规划"]):
        return "itinerary"
    else:
        return "finish"


def mock_weather(city: str) -> dict:
    """模拟查天气"""
    return {"city": city, "temperature": "25°C", "condition": "晴"}


def mock_flights(city: str) -> list:
    """模拟查航班"""
    return [{"airline": "CA", "price": 1200, "from": "上海", "to": city}]


def mock_hotels(city: str) -> list:
    """模拟查酒店"""
    return [{"name": f"{city}大酒店", "price": 500, "rating": 4.5}]


def mock_pois(city: str) -> list:
    """模拟查景点"""
    return [{"name": f"{city}热门景点", "rating": 4.8}]


# ── 3.2 手动实现状态机 ─────────────────────────────────────────────────────

class TravelPlanner:
    """
    手动实现的简化版旅行规划状态机
    
    目的：让你先理解"状态机"的流程，再看 LangGraph 的代码会觉得非常简单。
    """
    
    def __init__(self):
        self.state = {
            "messages": [],
            "destination": None,
            "weather_info": None,
            "flight_info": None,
            "hotel_info": None,
            "poi_info": None,
            "itinerary": None,
            "next": None,
        }

    def run(self, user_message: str):
        """运行一次完整的规划流程"""
        print(f"\n  用户: {user_message}")
        self.state["messages"].append(f"用户: {user_message}")

        # 提取目的地（简化版，实际用 LLM 提取）
        # 假设用户消息中包含城市名
        cities = ["北京", "上海", "广州", "深圳", "成都", "杭州", "三亚"]
        for city in cities:
            if city in user_message:
                self.state["destination"] = city
                break

        max_rounds = 5
        for round_num in range(max_rounds):
            print(f"\n  ── 第 {round_num + 1} 轮 ──")

            # Step 1: 意图识别（对应 intent_router 节点）
            last_message = self.state["messages"][-1] if self.state["messages"] else ""
            intent = mock_llm_classify(last_message)
            print(f"  意图识别: {intent}")

            # Step 2: 根据意图执行对应操作
            if intent == "weather" and self.state["destination"]:
                self.state["weather_info"] = mock_weather(self.state["destination"])
                print(f"  查天气: {self.state['weather_info']}")
                self.state["messages"].append(f"系统: 已查询{self.state['destination']}天气")

            elif intent == "flights" and self.state["destination"]:
                self.state["flight_info"] = mock_flights(self.state["destination"])
                print(f"  查航班: {self.state['flight_info']}")
                self.state["messages"].append(f"系统: 已查询{self.state['destination']}航班")

            elif intent == "hotels" and self.state["destination"]:
                self.state["hotel_info"] = mock_hotels(self.state["destination"])
                print(f"  查酒店: {self.state['hotel_info']}")
                self.state["messages"].append(f"系统: 已查询{self.state['destination']}酒店")

            elif intent == "pois" and self.state["destination"]:
                self.state["poi_info"] = mock_pois(self.state["destination"])
                print(f"  查景点: {self.state['poi_info']}")
                self.state["messages"].append(f"系统: 已查询{self.state['destination']}景点")

            elif intent == "itinerary":
                self.state["itinerary"] = {
                    "content": f"Day1: 游览{self.state['destination']}主要景点\n"
                               f"Day2: 体验当地美食\n"
                               f"Day3: 自由活动"
                }
                print(f"  生成行程: ✅")
                self.state["messages"].append(f"系统: 行程已生成")
                break

            elif intent == "finish":
                print(f"  信息足够，结束")
                break

        return self.state


def demo_manual_state_machine():
    """演示手动实现的状态机"""
    print("\n" + "=" * 60)
    print("  [PART 3] 手动实现状态机（理解流程）")
    print("=" * 60)

    planner = TravelPlanner()
    result = planner.run("我想去北京玩3天，帮我查查天气和景点，再生成一个行程")

    print(f"\n\n  最终状态:")
    for key, value in result.items():
        if key != "messages":
            print(f"    {key}: {value}")


# ============================================================================
#   Part 4: 项目中的 LangGraph 实现 —— 逐步拆解
# ============================================================================
#
# 现在回头看项目中的代码，你会发现一切都很熟悉。

# ── 4.1 导入项目中的实际代码 ───────────────────────────────────────────────
# 项目中的代码放在 graph/ 目录下：
#   state.py     → TravelState 定义
#   supervisor.py → 路由器（决定下一步去哪）
#   nodes.py     → 各个处理节点
#   builder.py   → 组装图

# 我们在这里重新实现一遍，但加详细注释

# ── 4.2 定义 State（对应 graph/state.py） ───────────────────────────────────

class TravelState(TypedDict):
    """
    项目中的 TravelState 完整版
    
    注意：这个 TypedDict 和项目的 graph/state.py 完全一致
    """
    messages: Annotated[list, operator.add]  # 对话历史（累加模式）
    user_id: Optional[int]                   # 用户 ID
    trip_id: Optional[int]                   # 行程 ID
    destination: Optional[str]               # 目的地
    dates: Optional[Dict]                    # 日期
    budget: Optional[Dict]                   # 预算
    travelers: Optional[int]                 # 出行人数
    preferences: Optional[Dict]              # 偏好
    weather_info: Optional[Dict]             # 天气信息
    flight_info: Optional[List[Dict]]        # 航班信息
    hotel_info: Optional[List[Dict]]         # 酒店信息
    poi_info: Optional[List[Dict]]           # 景点信息
    itinerary: Optional[Dict]                # 生成的行程
    next: Optional[str]                      # 下一步做什么


# ── 4.3 定义路由器（对应 graph/supervisor.py） ─────────────────────────────
# 项目中的路由器叫 supervisor，意思是"监督者"，
# 它的职责就是"看当前状态，决定下一步去哪"

def supervisor(state: TravelState) -> str:
    """
    项目中的 supervisor 函数 —— 完整版
    
    参数 state 是当前所有状态，路由器根据 state 的内容做决策。
    返回值是一个字符串，表示下一个要执行的节点名。
    
    项目中的原始代码（graph/supervisor.py）：
        def supervisor(state: TravelState) -> str:
            next_step = state.get("next", "finish")
            routes = {
                "weather": "weather",
                "flights": "flights",
                "hotels": "hotels",
                "pois": "pois",
                "itinerary": "itinerary",
                "finish": "end"
            }
            return routes.get(next_step, "end")
    """
    next_step = state.get("next", "finish")
    print(f"    [supervisor] next='{next_step}' → ", end="")

    # 路由表：state["next"] 的值 → 对应的节点名
    routes = {
        "weather": "weather",
        "flights": "flights",
        "hotels": "hotels",
        "pois": "pois",
        "itinerary": "itinerary",
        "finish": "end"
    }

    result = routes.get(next_step, "end")
    print(f"去 '{result}'")
    return result


# ── 4.4 定义节点（对应 graph/nodes.py） ────────────────────────────────────

# 先模拟一个 LLM（不用真实 API，用关键词匹配模拟）
def mock_llm(state: TravelState) -> str:
    """模拟 LLM 的意图识别"""
    if not state.get("messages"):
        return "finish"
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "content"):
        last_msg = last_msg.content
    return mock_llm_classify(str(last_msg))


def intent_router(state: TravelState) -> TravelState:
    """
    意图识别节点 —— 对应 graph/nodes.py 的 intent_router
    
    它的工作：
        1. 把用户最近的对话 + 系统提示词发给 LLM
        2. LLM 判断"下一步需要做什么"
        3. 把判断结果写入 state["next"]
    
    项目中的原始代码（简化）：
        def intent_router(state: TravelState) -> TravelState:
            system_prompt = "你是一个旅行规划助手的意图分类器..."
            messages = [SystemMessage(content=system_prompt)] + state["messages"][-5:]
            response = llm.invoke(messages)
            next_step = response.content.strip().lower()
            valid_next = ["weather", "flights", "hotels", "pois", "itinerary", "finish"]
            if next_step not in valid_next:
                next_step = "finish"
            return {"next": next_step}
    """
    print(f"  [intent_router] 分析用户意图...")

    # 模拟 LLM 调用
    next_step = mock_llm(state)

    # 校验返回值
    valid_next = ["weather", "flights", "hotels", "pois", "itinerary", "finish"]
    if next_step not in valid_next:
        next_step = "finish"

    print(f"    → 意图: {next_step}")
    return {"next": next_step}


def weather_node(state: TravelState) -> TravelState:
    """查天气节点 —— 对应 graph/nodes.py 的 weather_node"""
    print(f"  [weather_node] 查询天气...")
    if state.get("destination"):
        weather = mock_weather(state["destination"])
        print(f"    → {weather}")
        return {"weather_info": weather}
    print(f"    → 没有目的地，跳过")
    return {}


def flights_node(state: TravelState) -> TravelState:
    """查航班节点"""
    print(f"  [flights_node] 查询航班...")
    if state.get("destination"):
        flights = mock_flights(state["destination"])
        print(f"    → {flights}")
        return {"flight_info": flights}
    return {}


def hotels_node(state: TravelState) -> TravelState:
    """查酒店节点"""
    print(f"  [hotels_node] 查询酒店...")
    if state.get("destination"):
        hotels = mock_hotels(state["destination"])
        print(f"    → {hotels}")
        return {"hotel_info": hotels}
    return {}


def pois_node(state: TravelState) -> TravelState:
    """查景点节点"""
    print(f"  [pois_node] 查询景点...")
    if state.get("destination"):
        pois = mock_pois(state["destination"])
        print(f"    → {pois}")
        return {"poi_info": pois}
    return {}


def itinerary_node(state: TravelState) -> TravelState:
    """
    生成行程节点 —— 对应 graph/nodes.py 的 itinerary_node
    
    这是最后一个节点，也是信息最密集的节点。
    它把前面收集到的所有信息（天气/航班/酒店/景点）拼成上下文，
    让 LLM 生成一份完整的行程规划。
    """
    print(f"  [itinerary_node] 生成行程规划...")

    context = f"""
    目的地：{state.get('destination', '未指定')}
    日期：{state.get('dates', {})}
    预算：{state.get('budget', {})}
    出行人数：{state.get('travelers', 1)}
    天气信息：{state.get('weather_info', {})}
    航班信息：{state.get('flight_info', [])}
    酒店信息：{state.get('hotel_info', [])}
    景点信息：{state.get('poi_info', [])}
    """

    # 模拟 LLM 生成行程
    itinerary_text = (
        f"📋 {state.get('destination', '目的地')} 行程规划\n\n"
        f"Day 1:\n"
        f"  上午：抵达目的地，入住酒店\n"
        f"  下午：游览主要景点\n"
        f"  晚上：品尝当地美食\n\n"
        f"Day 2:\n"
        f"  上午：继续探索景点\n"
        f"  下午：休闲购物\n"
        f"  晚上：自由活动\n\n"
        f"Day 3:\n"
        f"  上午：最后游览\n"
        f"  下午：返程\n"
    )

    print(f"    → 行程已生成")
    return {
        "itinerary": {"content": itinerary_text},
        "next": "finish",  # 告诉 supervisor：已经结束，不要再循环了
    }


# ── 4.5 组装成图（对应 graph/builder.py） ──────────────────────────────────

def build_travel_planner_graph():
    """
    构建完整的旅行规划图 —— 和项目中的 builder.py 完全对应
    
    图结构：
        intent_router ──→ supervisor ──→ weather/flights/hotels/pois
              ↑                              │（执行完工具后）
              └───────── 回到 intent_router ←─┘
              
              intent_router ──→ supervisor ──→ itinerary → END
    """
    from langgraph.graph import StateGraph, END

    workflow = StateGraph(TravelState)

    # 添加节点
    workflow.add_node("intent_router", intent_router)
    workflow.add_node("weather", weather_node)
    workflow.add_node("flights", flights_node)
    workflow.add_node("hotels", hotels_node)
    workflow.add_node("pois", pois_node)
    workflow.add_node("itinerary", itinerary_node)

    # 设置入口
    workflow.set_entry_point("intent_router")

    # 意图识别后的条件路由
    workflow.add_conditional_edges(
        "intent_router",
        supervisor,
        {
            "weather": "weather",
            "flights": "flights",
            "hotels": "hotels",
            "pois": "pois",
            "itinerary": "itinerary",
            "end": END,
        }
    )

    # 工具节点执行完后，回到 intent_router 再次分析
    workflow.add_edge("weather", "intent_router")
    workflow.add_edge("flights", "intent_router")
    workflow.add_edge("hotels", "intent_router")
    workflow.add_edge("pois", "intent_router")

    # 生成行程后结束
    workflow.add_edge("itinerary", END)

    return workflow.compile()


def demo_project_langgraph():
    """运行项目中的 LangGraph 实现"""
    print("\n" + "=" * 60)
    print("  [PART 4] 项目中的 LangGraph 实现")
    print("=" * 60)

    graph = build_travel_planner_graph()

    # 模拟用户消息（用 HumanMessage 类型）
    from langchain_core.messages import HumanMessage

    print("\n  ▶ 测试: '我想去北京玩3天，查查天气和景点，帮我规划行程'")
    print()

    initial_state = {
        "messages": [HumanMessage(content="我想去北京玩3天，查查天气和景点，帮我规划行程")],
        "user_id": 1,
        "trip_id": None,
        "destination": "北京",
        "dates": {"start": "2026-09-01", "end": "2026-09-03"},
        "budget": {"min": 3000, "max": 8000},
        "travelers": 2,
        "preferences": None,
        "weather_info": None,
        "flight_info": None,
        "hotel_info": None,
        "poi_info": None,
        "itinerary": None,
        "next": None,
    }

    print(f"  ┌────────────────────────────────────────────────────┐")
    print(f"  │                  开始执行                          │")
    print(f"  └────────────────────────────────────────────────────┘")
    print()

    result = graph.invoke(initial_state)

    print(f"\n  ┌────────────────────────────────────────────────────┐")
    print(f"  │                  执行完成                          │")
    print(f"  └────────────────────────────────────────────────────┘")
    print(f"\n  最终行程:")
    print(f"  {result['itinerary']['content']}")


# ============================================================================
#   Part 5: 深入理解条件边（Conditional Edge）
# ============================================================================
#
# 条件边是 LangGraph 中最核心的概念，也是项目中最关键的设计。

def demo_conditional_edges():
    """深入理解条件边"""
    print("\n" + "=" * 60)
    print("  [PART 5] 条件边深入理解")
    print("=" * 60)

    print("""
    ┌────────────────────────────────────────────────────────────────┐
    │                    条件边（Conditional Edge）                    │
    ├────────────────────────────────────────────────────────────────┤
    │                                                                  │
    │  普通边：A → B（无条件的，执行完 A 一定执行 B）                    │
    │  条件边：A → [路由器] → B 或 C（根据状态决定）                    │
    │                                                                  │
    │  项目中的条件边：                                                │
    │                                                                  │
    │    intent_router ──→ supervisor ──→ weather（如果 next=weather）  │
    │                        │           → flights（如果 next=flights） │
    │                        │           → hotels（如果 next=hotels）   │
    │                        │           → pois（如果 next=pois）       │
    │                        │           → itinerary（如果 next=itinerary）│
    │                        │           → END（如果 next=finish）      │
    │                                                                  │
    │  add_conditional_edges 的参数：                                  │
    │    1. 起点（哪个节点执行完后触发）                                │
    │    2. 路由器函数（根据 state 返回下一个节点的名字）                │
    │    3. 映射字典（路由器返回值 → 实际节点名）                      │
    └────────────────────────────────────────────────────────────────┘
    """)

    # 展示项目中的实际代码
    print("  ▶ 项目 builder.py 中的条件边代码:")
    print("""
    workflow.add_conditional_edges(
        "intent_router",                  # 起点：intent_router 节点执行完后
        supervisor,                        # 路由器：根据 state 返回字符串
        {                                  # 映射：路由器返回值 → 目标节点
            "weather": "weather",          # 如果 supervisor 返回 "weather"
            "flights": "flights",          # 如果 supervisor 返回 "flights"
            "hotels": "hotels",
            "pois": "pois",
            "itinerary": "itinerary",
            "end": END                     # 如果 supervisor 返回 "end"
        }
    )
    """)

    print("""
  ┌────────────────────────────────────────────────────────────────┐
  │                    关键理解                                     │
  ├────────────────────────────────────────────────────────────────┤
  │                                                                  │
  │  1. intent_router 节点让 LLM 判断"用户想要什么"                    │
  │  2. 判断结果写入 state["next"]                                   │
  │  3. supervisor 路由器读取 state["next"]，返回对应的节点名          │
  │  4. LangGraph 根据映射字典找到目标节点，跳转过去                   │
  │  5. 工具节点执行完后，通过普通边回到 intent_router                │
  │  6. 重复 1-5，直到 supervisor 返回 "end"                         │
  │                                                                  │
  └────────────────────────────────────────────────────────────────┘
    """)


# ============================================================================
#   Part 6: 流式输出（对应 api/stream.py）
# ============================================================================

def demo_streaming():
    """演示流式输出"""
    print("\n" + "=" * 60)
    print("  [PART 6] 流式输出（SSE）")
    print("=" * 60)

    print("""
    ┌────────────────────────────────────────────────────────────────┐
    │                    流式输出架构                                 │
    ├────────────────────────────────────────────────────────────────┤
    │                                                                  │
    │  后端（api/stream.py）：                                        │
    │    travel_graph.astream_events(initial_state, version="v1")     │
    │      ↓                                                          │
    │    监听 on_chat_model_stream 事件                               │
    │      ↓                                                          │
    │    每个 token 拼成 SSE 格式：                                    │
    │      data: {"type": "token", "content": "今"}                  │
    │      data: {"type": "token", "content": "天"}                  │
    │      data: {"type": "token", "content": "天"}                  │
    │      data: {"type": "token", "content": "气"}                  │
    │      ...                                                       │
    │                                                                  │
    │  前端（stores/chat.ts）：                                       │
    │    fetch(url) → reader.read() → 逐行解析 SSE 数据               │
    │    → 每次收到 token 就追加到消息内容中 → 实时渲染               │
    │                                                                  │
    │  效果：AI 的回复像"打字机"一样逐字显示，用户不用等全部生成完      │
    │                                                                  │
    └────────────────────────────────────────────────────────────────┘
    """)

    # 模拟流式输出
    print("  ▶ 模拟流式输出过程:")
    text = "今天天气晴朗，适合出游。"
    for char in text:
        print(f"    data: {json.dumps({'type': 'token', 'content': char})}")
    print(f"    data: {json.dumps({'type': 'end'})}")
    print(f"    → 前端渲染结果: {text}")


# ============================================================================
#   Part 7: 常见陷阱与 FAQ
# ============================================================================

def faq():
    """常见问题"""
    print("\n" + "=" * 60)
    print("  [PART 7] 常见陷阱与 FAQ")
    print("=" * 60)

    faqs = [
        ("Q: 为什么工具节点执行完要回到 intent_router，而不是直接去下一个工具？",
         "A: 因为 LLM 需要根据工具返回的结果，决定下一步做什么。"
         "比如查完天气发现下雨，可能就跳过景点推荐，直接推荐室内活动。"
         "每次回到 intent_router 让 LLM 重新决策，比硬编码流程更灵活。"),

        ("Q: Annotated[list, operator.add] 是什么意思？",
         "A: 告诉 LangGraph 这个字段的更新方式是"追加"而不是"覆盖"。"
         "普通字段：return {'next': 'weather'} 会覆盖原来的 next。"
         "messages 字段：return {'messages': [new_msg]} 会把新消息追加到列表末尾。"
         "这是实现多轮对话记忆的关键。"),

        ("Q: 为什么用 StateGraph 而不是单纯调 LLM？",
         "A: 复杂任务需要多步协作。比如：查天气 → 查航班 → 查酒店 → 查景点 → 生成行程。"
         "如果一次 LLM 调用完成，token 太长容易出错，且无法查实时数据。"
         "StateGraph 让 LLM 可以"分步执行"，每次只做一件事，效率和质量都更高。"),

        ("Q: intent_router 节点和 supervisor 节点什么关系？",
         "A: intent_router 是"生成决策"的节点（调用 LLM 判断下一步）。"
         "supervisor 是"执行决策"的路由器（根据决策结果跳转）。"
         "两者配合：一个负责想，一个负责走。"),

        ("Q: 如果 LLM 返回了不在 valid_next 里的值怎么办？",
         "A: 项目中有兜底处理：if next_step not in valid_next: next_step = 'finish'"
         "永远不会因为 LLM 抽风导致程序崩溃。"),

        ("Q: LangGraph 和普通状态机（如 Python 的 transitions 库）有什么区别？",
         "A: LangGraph 专门为 LLM 场景设计，支持："
         "1. 流式输出（astream_events）"
         "2. 状态累加（Annotated）"
         "3. 与 LangChain 生态集成（ChatModel、Tool 等）"
         "4. 图可视化、断点调试等高级功能"),
    ]

    for i, (q, a) in enumerate(faqs, 1):
        print(f"\n  ── FAQ {i} ──────────────────────────────────────")
        print(f"  {q}")
        print(f"  {a}")


# ============================================================================
#   Part 8: 架构图
# ============================================================================

def architecture_diagram():
    """打印架构图"""
    print("\n" + "=" * 60)
    print("  [PART 8] 项目 LangGraph 完整架构图")
    print("=" * 60)

    print("""
    ┌─────────────────────────────────────────────────────────────────┐
    │                  Travel Planner LangGraph 架构                   │
    └─────────────────────────────────────────────────────────────────┘

    入口（api/stream.py）
    │
    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    travel_graph.astream_events                   │
    │                                                                  │
    │  ┌──────────────┐                                                │
    │  │ intent_router│ ◄──────────────────────────────┐               │
    │  │ (LLM 判断意图) │                                │               │
    │  └──────┬───────┘                                │               │
    │         │                                        │               │
    │         ▼                                        │               │
    │  ┌──────────────┐                                │               │
    │  │   supervisor  │  ← 路由器                       │               │
    │  │ (条件边)      │                                │               │
    │  └──┬──┬──┬──┬──┘                                │               │
    │     │  │  │  │                                    │               │
    │     ▼  ▼  ▼  ▼                                    │               │
    │  ┌──┐ ┌──┐ ┌──┐ ┌──┐                              │               │
    │  │W │ │F │ │H │ │P │  各工具节点                   │               │
    │  │ea│ │li│ │ot│ │oi│  执行完后                      │               │
    │  │th│ │gh│ │el│ │s │  回到 intent_router ──────────┘               │
    │  │er│ │ts│ │s │ │  │                              │               │
    │  └──┘ └──┘ └──┘ └──┘                              │               │
    │         │                                        │               │
    │         ▼                                        │               │
    │  ┌──────────────┐                                │               │
    │  │  itinerary   │  ← 生成行程                      │               │
    │  └──────┬───────┘                                │               │
    │         │                                        │               │
    │         ▼                                        │               │
    │     ┌──────┐                                     │               │
    │     │ END  │                                     │               │
    │     └──────┘                                     │               │
    └─────────────────────────────────────────────────────────────────┘

    关键数据流：
        state["next"] = "weather"  →  supervisor 路由到 weather 节点
        state["next"] = "flights"  →  supervisor 路由到 flights 节点
        state["next"] = "itinerary" → supervisor 路由到 itinerary 节点
        state["next"] = "finish"   →  supervisor 路由到 END
    """)


# ============================================================================
#   主函数
# ============================================================================

async def main():
    """运行所有演示"""
    print("=" * 70)
    print("  LangGraph 状态机学习之旅")
    print("  基于 Travel Planner 项目实战")
    print("=" * 70)

    # Part 1: 最简状态机
    demo_simple_graph()

    # Part 2: 项目中的 State
    demo_travel_state()

    # Part 3: 手动实现状态机
    demo_manual_state_machine()

    # Part 4: 项目中的 LangGraph 实现
    demo_project_langgraph()

    # Part 5: 条件边深入
    demo_conditional_edges()

    # Part 6: 流式输出
    demo_streaming()

    # Part 7: FAQ
    faq()

    # Part 8: 架构图
    architecture_diagram()

    print("\n" + "=" * 70)
    print("  🎉 学习完成！")
    print("=" * 70)
    print("""
  建议下一步：
    1. 打开 backend/app/graph/state.py 看 State 定义
    2. 打开 backend/app/graph/supervisor.py 看路由器
    3. 打开 backend/app/graph/nodes.py 看各节点实现
    4. 打开 backend/app/graph/builder.py 看如何组装图
    5. 打开 backend/app/api/stream.py 看流式输出
    """)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())