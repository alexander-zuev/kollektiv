# Content for item 0

```markdown
Contents Menu Expand Light mode Dark mode Auto light/dark mode

[Back to top](#)

Toggle Light / Dark / Auto color theme

Toggle table of contents sidebar

Real-Time Data[#](#real-time-data "Permalink to this heading")

===============================================================

StockDataStream[#](#stockdatastream "Permalink to this heading")

-----------------------------------------------------------------

_class_ alpaca.data.live.stock.StockDataStream(_api\_key: str_, _secret\_key: str_, _raw\_data: bool \= False_, _feed: [DataFeed](../enums.html#alpaca.data.enums.DataFeed "alpaca.data.enums.DataFeed")
 \= DataFeed.IEX_, _websocket\_params: Optional\[Dict\] \= None_, _url\_override: Optional\[str\] \= None_)[#](#alpaca.data.live.stock.StockDataStream "Permalink to this definition")

A WebSocket client for streaming live stock data.

_async_ close() → None[#](#alpaca.data.live.stock.StockDataStream.close "Permalink to this definition")

Closes the websocket connection.

register\_trade\_cancels(_handler: Callable\[\[Union\[TradeCancel, Dict\]\], Awaitable\[None\]\]_) → None[#](#alpaca.data.live.stock.StockDataStream.register_trade_cancels "Permalink to this definition")

Register a trade cancel handler. You can only subscribe to trade cancels by subscribing to the underlying trades.

Parameters:

**handler** (_Callable__\[__\[__Union__\[__TradeCancel__,_ _Dict__\]__\]__,_ _Awaitable__\[__None__\]__\]_) – The coroutine callback function to handle the incoming data.

register\_trade\_corrections(_handler: Callable\[\[Union\[TradeCorrection, Dict\]\], Awaitable\[None\]\]_) → None[#](#alpaca.data.live.stock.StockDataStream.register_trade_corrections "Permalink to this definition")

Register a trade correction handler. You can only subscribe to trade corrections by subscribing to the underlying trades.

Parameters:

**handler** (_Callable__\[__\[__Union__\[__TradeCorrection__,_ _Dict__\]__\]_) – The coroutine callback function to handle the incoming data.\
\
run() → None[#](#alpaca.data.live.stock.StockDataStream.run "Permalink to this definition")\
\
Starts up the websocket connection’s event loop\
\
stop() → None[#](#alpaca.data.live.stock.StockDataStream.stop "Permalink to this definition")\
\
Stops the websocket connection.\
\
_async_ stop\_ws() → None[#](#alpaca.data.live.stock.StockDataStream.stop_ws "Permalink to this definition")\
\
Signals websocket connection should close by adding a closing message to the stop\_stream\_queue\
\
subscribe\_bars(_handler: Callable\[\[Union\[[Bar](../models.html#alpaca.data.models.bars.Bar "alpaca.data.models.bars.Bar")\
, Dict\]\], Awaitable\[None\]\]_, _\*symbols: str_) → None[#](#alpaca.data.live.stock.StockDataStream.subscribe_bars "Permalink to this definition")\
\
Subscribe to minute bars\
\
Parameters:\
\
*   **handler** (_Callable__\[__\[__Union__\[_[_Trade_](../models.html#alpaca.data.models.trades.Trade "alpaca.data.models.trades.Trade")\
    _,_ _Dict__\]__\]__,_ _Awaitable__\[__None__\]__\]_) – The coroutine callback function to handle the incoming data.\
    \
*   **\*symbols** – List of ticker symbols to subscribe to. “\*” for everything.\
    \
\
subscribe\_daily\_bars(_handler: Callable\[\[Union\[[Bar](../models.html#alpaca.data.models.bars.Bar "alpaca.data.models.bars.Bar")\
, Dict\]\], Awaitable\[None\]\]_, _\*symbols: str_) → None[#](#alpaca.data.live.stock.StockDataStream.subscribe_daily_bars "Permalink to this definition")\
\
Subscribe to daily bars\
\
Parameters:\
\
*   **handler** (_Callable__\[__\[__Union__\[_[_Bar_](../models.html#alpaca.data.models.bars.Bar "alpaca.data.models.bars.Bar")\
    _,_ _Dict__\]__\]__,_ _Awaitable__\[__None__\]__\]_) – The coroutine callback function to handle the incoming data.\
    \
*   **\*symbols** – List of ticker symbols to subscribe to. “\*” for everything.\
    \
\
subscribe\_quotes(_handler: Callable\[\[Union\[[Quote](../models.html#alpaca.data.models.quotes.Quote "alpaca.data.models.quotes.Quote")\
, Dict\]\], Awaitable\[None\]\]_, _\*symbols: str_) → None[#](#alpaca.data.live.stock.StockDataStream.subscribe_quotes "Permalink to this definition")\
\
Subscribe to quotes\
\
Parameters:\
\
*   **handler** (_Callable__\[__\[__Union__\[_[_Trade_](../models.html#alpaca.data.models.trades.Trade "alpaca.data.models.trades.Trade")\
    _,_ _Dict__\]__\]__,_ _Awaitable__\[__None__\]__\]_) – The coroutine callback function to handle the incoming data.\
    \
*   **\*symbols** – List of ticker symbols to subscribe to. “\*” for everything.\
    \
\
subscribe\_trades(_handler: Callable\[\[Union\[[Trade](../models.html#alpaca.data.models.trades.Trade "alpaca.data.models.trades.Trade")\
, Dict\]\], Awaitable\[None\]\]_, _\*symbols: str_) → None[#](#alpaca.data.live.stock.StockDataStream.subscribe_trades "Permalink to this definition")\
\
Subscribe to trades.\
\
Parameters:\
\
*   **handler** (_Callable__\[__\[__Union__\[_[_Trade_](../models.html#alpaca.data.models.trades.Trade "alpaca.data.models.trades.Trade")\
    _,_ _Dict__\]__\]__,_ _Awaitable__\[__None__\]__\]_) – The coroutine callback function to handle the incoming data.\
    \
*   **\*symbols** – List of ticker symbols to subscribe to. “\*” for everything.\
    \
\
subscribe\_trading\_statuses(_handler: Callable\[\[Union\[TradingStatus, Dict\]\], Awaitable\[None\]\]_, _\*symbols_) → None[#](#alpaca.data.live.stock.StockDataStream.subscribe_trading_statuses "Permalink to this definition")\
\
Subscribe to trading statuses (halts, resumes)\
\
Parameters:\
\
*   **handler** (_Callable__\[__\[__Union__\[__TradingStatus__,_ _Dict__\]__\]__,_ _Awaitable__\[__None__\]__\]_) – The coroutine callback function to handle the incoming data.\
    \
*   **\*symbols** – List of ticker symbols to subscribe to. “\*” for everything.\
    \
\
subscribe\_updated\_bars(_handler: Callable\[\[Union\[[Bar](../models.html#alpaca.data.models.bars.Bar "alpaca.data.models.bars.Bar")\
, Dict\]\], Awaitable\[None\]\]_, _\*symbols: str_) → None[#](#alpaca.data.live.stock.StockDataStream.subscribe_updated_bars "Permalink to this definition")\
\
Subscribe to updated minute bars\
\
Parameters:\
\
*   **handler** (_Callable__\[__\[__Union__\[_[_Bar_](../models.html#alpaca.data.models.bars.Bar "alpaca.data.models.bars.Bar")\
    _,_ _Dict__\]__\]__,_ _Awaitable__\[__None__\]__\]_) – The coroutine callback function to handle the incoming data.\
    \
*   **\*symbols** – List of ticker symbols to subscribe to. “\*” for everything.\
    \
\
unsubscribe\_bars(_\*symbols: str_) → None[#](#alpaca.data.live.stock.StockDataStream.unsubscribe_bars "Permalink to this definition")\
\
Unsubscribe from minute bars\
\
Parameters:\
\
**\*symbols** (_str_) – List of ticker symbols to unsubscribe from. “\*” for everything.\
\
unsubscribe\_daily\_bars(_\*symbols: str_) → None[#](#alpaca.data.live.stock.StockDataStream.unsubscribe_daily_bars "Permalink to this definition")\
\
Unsubscribe from daily bars\
\
Parameters:\
\
**\*symbols** (_str_) – List of ticker symbols to unsubscribe from. “\*” for everything.\
\
unsubscribe\_quotes(_\*symbols: str_) → None[#](#alpaca.data.live.stock.StockDataStream.unsubscribe_quotes "Permalink to this definition")\
\
Unsubscribe from quotes\
\
Parameters:\
\
**\*symbols** (_str_) – List of ticker symbols to unsubscribe from. “\*” for everything.\
\
unsubscribe\_trades(_\*symbols: str_) → None[#](#alpaca.data.live.stock.StockDataStream.unsubscribe_trades "Permalink to this definition")\
\
Unsubscribe from trades\
\
Parameters:\
\
**\*symbols** (_str_) – List of ticker symbols to unsubscribe from. “\*” for everything.\
\
unsubscribe\_trading\_statuses(_\*symbols: str_) → None[#](#alpaca.data.live.stock.StockDataStream.unsubscribe_trading_statuses "Permalink to this definition")\
\
Unsubscribe from trading statuses\
\
Parameters:\
\
**\*symbols** (_str_) – List of ticker symbols to unsubscribe from. “\*” for everything.\
\
unsubscribe\_updated\_bars(_\*symbols: str_) → None[#](#alpaca.data.live.stock.StockDataStream.unsubscribe_updated_bars "Permalink to this definition")\
\
Unsubscribe from updated bars\
\
Parameters:\
\
**\*symbols** (_str_) – List of ticker symbols to unsubscribe from. “\*” for everything.
```

----

