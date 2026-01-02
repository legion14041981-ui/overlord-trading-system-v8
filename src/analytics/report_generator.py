"""Report Generator for Portfolio Performance Reports.

Generates comprehensive reports in multiple formats:
- JSON (for APIs)
- HTML (for web viewing)
- PDF (for distribution)
- CSV (for analysis)
"""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from pathlib import Path
import pandas as pd

from .performance_analyzer import PerformanceAnalyzer, PerformanceMetrics
from .metrics_calculator import MetricsCalculator
from ..core.logging import structured_logger


class ReportGenerator:
    """Generates comprehensive performance reports.
    
    Features:
    - Multi-format output (JSON, HTML, CSV)
    - Customizable report sections
    - Period comparison
    - Visual equity curve data
    - Trade log export
    """
    
    def __init__(
        self,
        performance_analyzer: PerformanceAnalyzer,
        metrics_calculator: MetricsCalculator,
        output_dir: Optional[Path] = None,
    ):
        self.analyzer = performance_analyzer
        self.calculator = metrics_calculator
        self.output_dir = output_dir or Path("./reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = structured_logger.get_logger(__name__)
        
    async def generate_json_report(
        self,
        include_trades: bool = True,
        include_equity_curve: bool = True,
    ) -> Dict:
        """Generate comprehensive JSON report.
        
        Args:
            include_trades: Include trade history
            include_equity_curve: Include equity curve data
            
        Returns:
            Report dictionary
        """
        # Get performance metrics
        metrics = await self.analyzer.calculate_metrics()
        
        # Get attribution
        attribution = await self.analyzer.get_attribution()
        
        # Build report
        report = {
            "report_timestamp": datetime.utcnow().isoformat(),
            "initial_capital": float(self.analyzer.initial_capital),
            "current_capital": float(self.analyzer.current_capital),
            "metrics": metrics.to_dict(),
            "attribution": {
                symbol: float(pnl) for symbol, pnl in attribution.items()
            },
        }
        
        # Add equity curve
        if include_equity_curve and self.analyzer.equity_curve:
            report["equity_curve"] = [
                {
                    "timestamp": ts.isoformat(),
                    "equity": float(equity),
                }
                for ts, equity in self.analyzer.equity_curve
            ]
            
        # Add trade history
        if include_trades:
            report["trades"] = [
                {
                    "timestamp": trade["timestamp"].isoformat(),
                    "symbol": trade["symbol"],
                    "side": trade["side"].value,
                    "quantity": float(trade["quantity"]),
                    "price": float(trade["price"]),
                    "pnl": float(trade["pnl"]),
                }
                for trade in self.analyzer.trade_history
            ]
            
        self.logger.info(
            "json_report_generated",
            num_trades=len(self.analyzer.trade_history) if include_trades else 0,
            equity_points=len(self.analyzer.equity_curve) if include_equity_curve else 0,
        )
        
        return report
        
    async def save_json_report(
        self,
        filename: Optional[str] = None,
        **kwargs,
    ) -> Path:
        """Generate and save JSON report to file.
        
        Args:
            filename: Output filename (auto-generated if None)
            **kwargs: Arguments for generate_json_report
            
        Returns:
            Path to saved report
        """
        report = await self.generate_json_report(**kwargs)
        
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"
            
        filepath = self.output_dir / filename
        
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
            
        self.logger.info("json_report_saved", filepath=str(filepath))
        return filepath
        
    async def generate_html_report(
        self,
        title: str = "Portfolio Performance Report",
    ) -> str:
        """Generate HTML report.
        
        Args:
            title: Report title
            
        Returns:
            HTML content as string
        """
        metrics = await self.analyzer.calculate_metrics()
        attribution = await self.analyzer.get_attribution()
        
        # Build HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 32px;
        }}
        .header .timestamp {{
            opacity: 0.9;
            margin-top: 10px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-card .label {{
            color: #666;
            font-size: 14px;
            margin-bottom: 8px;
        }}
        .metric-card .value {{
            font-size: 28px;
            font-weight: bold;
            color: #333;
        }}
        .metric-card .value.positive {{
            color: #10b981;
        }}
        .metric-card .value.negative {{
            color: #ef4444;
        }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .section h2 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}
        th {{
            background-color: #f9fafb;
            font-weight: 600;
            color: #374151;
        }}
        tr:hover {{
            background-color: #f9fafb;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <div class="timestamp">Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
    </div>
    
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="label">Total Return</div>
            <div class="value {'positive' if metrics.total_return > 0 else 'negative'}">
                {metrics.total_return:.2%}
            </div>
        </div>
        <div class="metric-card">
            <div class="label">Sharpe Ratio</div>
            <div class="value">
                {float(metrics.sharpe_ratio):.2f if metrics.sharpe_ratio else 'N/A'}
            </div>
        </div>
        <div class="metric-card">
            <div class="label">Max Drawdown</div>
            <div class="value negative">
                {metrics.max_drawdown:.2%}
            </div>
        </div>
        <div class="metric-card">
            <div class="label">Win Rate</div>
            <div class="value">
                {metrics.win_rate:.1%}
            </div>
        </div>
        <div class="metric-card">
            <div class="label">Profit Factor</div>
            <div class="value">
                {float(metrics.profit_factor):.2f}
            </div>
        </div>
        <div class="metric-card">
            <div class="label">Total Trades</div>
            <div class="value">
                {metrics.total_trades}
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>Performance Metrics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Cumulative P&L</td>
                <td>${metrics.cumulative_pnl:,.2f}</td>
            </tr>
            <tr>
                <td>Realized P&L</td>
                <td>${metrics.realized_pnl:,.2f}</td>
            </tr>
            <tr>
                <td>Unrealized P&L</td>
                <td>${metrics.unrealized_pnl:,.2f}</td>
            </tr>
            <tr>
                <td>Sortino Ratio</td>
                <td>{float(metrics.sortino_ratio):.2f if metrics.sortino_ratio else 'N/A'}</td>
            </tr>
            <tr>
                <td>Calmar Ratio</td>
                <td>{float(metrics.calmar_ratio):.2f if metrics.calmar_ratio else 'N/A'}</td>
            </tr>
            <tr>
                <td>Volatility (Annualized)</td>
                <td>{metrics.volatility:.2%} if metrics.volatility else 'N/A'}</td>
            </tr>
            <tr>
                <td>VaR (95%)</td>
                <td>{metrics.var_95:.2%} if metrics.var_95 else 'N/A'}</td>
            </tr>
        </table>
    </div>
    
    <div class="section">
        <h2>Trade Statistics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Total Trades</td>
                <td>{metrics.total_trades}</td>
            </tr>
            <tr>
                <td>Winning Trades</td>
                <td>{metrics.winning_trades}</td>
            </tr>
            <tr>
                <td>Losing Trades</td>
                <td>{metrics.losing_trades}</td>
            </tr>
            <tr>
                <td>Average Win</td>
                <td>${metrics.avg_win:,.2f}</td>
            </tr>
            <tr>
                <td>Average Loss</td>
                <td>${metrics.avg_loss:,.2f}</td>
            </tr>
            <tr>
                <td>Largest Win</td>
                <td>${metrics.largest_win:,.2f}</td>
            </tr>
            <tr>
                <td>Largest Loss</td>
                <td>${metrics.largest_loss:,.2f}</td>
            </tr>
        </table>
    </div>
    
    <div class="section">
        <h2>P&L Attribution by Symbol</h2>
        <table>
            <tr>
                <th>Symbol</th>
                <th>P&L</th>
                <th>% of Total</th>
            </tr>
"""
        
        # Add attribution rows
        total_pnl = sum(attribution.values())
        for symbol, pnl in sorted(attribution.items(), key=lambda x: x[1], reverse=True):
            pct = (pnl / total_pnl * 100) if total_pnl != 0 else 0
            pnl_class = "positive" if pnl > 0 else "negative"
            html += f"""
            <tr>
                <td>{symbol}</td>
                <td class="{pnl_class}">${float(pnl):,.2f}</td>
                <td>{float(pct):.1f}%</td>
            </tr>
"""
        
        html += """
        </table>
    </div>
</body>
</html>
"""
        
        self.logger.info("html_report_generated")
        return html
        
    async def save_html_report(
        self,
        filename: Optional[str] = None,
        **kwargs,
    ) -> Path:
        """Generate and save HTML report.
        
        Args:
            filename: Output filename (auto-generated if None)
            **kwargs: Arguments for generate_html_report
            
        Returns:
            Path to saved report
        """
        html = await self.generate_html_report(**kwargs)
        
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.html"
            
        filepath = self.output_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
            
        self.logger.info("html_report_saved", filepath=str(filepath))
        return filepath
        
    async def generate_csv_exports(
        self,
        prefix: Optional[str] = None,
    ) -> Dict[str, Path]:
        """Generate CSV exports for all data.
        
        Args:
            prefix: Filename prefix (timestamp if None)
            
        Returns:
            Dictionary mapping data type to file path
        """
        if prefix is None:
            prefix = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            
        exports = {}
        
        # Export equity curve
        if self.analyzer.equity_curve:
            equity_df = pd.DataFrame(
                self.analyzer.equity_curve,
                columns=["timestamp", "equity"],
            )
            equity_path = self.output_dir / f"{prefix}_equity_curve.csv"
            equity_df.to_csv(equity_path, index=False)
            exports["equity_curve"] = equity_path
            
        # Export trades
        if self.analyzer.trade_history:
            trades_data = []
            for trade in self.analyzer.trade_history:
                trades_data.append({
                    "timestamp": trade["timestamp"],
                    "symbol": trade["symbol"],
                    "side": trade["side"].value,
                    "quantity": float(trade["quantity"]),
                    "price": float(trade["price"]),
                    "pnl": float(trade["pnl"]),
                })
            trades_df = pd.DataFrame(trades_data)
            trades_path = self.output_dir / f"{prefix}_trades.csv"
            trades_df.to_csv(trades_path, index=False)
            exports["trades"] = trades_path
            
        # Export metrics
        metrics = await self.analyzer.calculate_metrics()
        metrics_df = pd.DataFrame([metrics.to_dict()])
        metrics_path = self.output_dir / f"{prefix}_metrics.csv"
        metrics_df.to_csv(metrics_path, index=False)
        exports["metrics"] = metrics_path
        
        # Export attribution
        attribution = await self.analyzer.get_attribution()
        if attribution:
            attribution_data = [
                {"symbol": symbol, "pnl": float(pnl)}
                for symbol, pnl in attribution.items()
            ]
            attribution_df = pd.DataFrame(attribution_data)
            attribution_path = self.output_dir / f"{prefix}_attribution.csv"
            attribution_df.to_csv(attribution_path, index=False)
            exports["attribution"] = attribution_path
            
        self.logger.info(
            "csv_exports_generated",
            num_exports=len(exports),
            exports=list(exports.keys()),
        )
        
        return exports
        
    async def generate_summary(
        self,
        period: Optional[str] = None,
    ) -> str:
        """Generate text summary of performance.
        
        Args:
            period: Time period description
            
        Returns:
            Text summary
        """
        metrics = await self.analyzer.calculate_metrics()
        
        period_str = f" for {period}" if period else ""
        
        summary = f"""Performance Summary{period_str}
{'=' * 50}

Capital:
  Initial: ${float(self.analyzer.initial_capital):,.2f}
  Current: ${float(self.analyzer.current_capital):,.2f}
  Change:  {float(metrics.total_return):.2%}

Returns:
  Total Return:    {float(metrics.total_return):.2%}
  Sharpe Ratio:    {float(metrics.sharpe_ratio):.2f if metrics.sharpe_ratio else 'N/A'}
  Sortino Ratio:   {float(metrics.sortino_ratio):.2f if metrics.sortino_ratio else 'N/A'}
  Max Drawdown:    {float(metrics.max_drawdown):.2%}

Trades:
  Total:    {metrics.total_trades}
  Winners:  {metrics.winning_trades}
  Losers:   {metrics.losing_trades}
  Win Rate: {float(metrics.win_rate):.1%}

P&L:
  Realized:   ${float(metrics.realized_pnl):,.2f}
  Unrealized: ${float(metrics.unrealized_pnl):,.2f}
  Total:      ${float(metrics.cumulative_pnl):,.2f}

Risk:
  Volatility:  {float(metrics.volatility):.2%} if metrics.volatility else 'N/A'}
  VaR (95%):   {float(metrics.var_95):.2%} if metrics.var_95 else 'N/A'}
  CVaR (95%):  {float(metrics.cvar_95):.2%} if metrics.cvar_95 else 'N/A'}
"""
        
        return summary
