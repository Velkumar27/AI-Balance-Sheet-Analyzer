import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List, Any
import numpy as np
import streamlit as st

def render_trend_chart(metrics_data: Dict[str, Any]):
    """
    Renders clean Plotly visualizations for:
    1. Revenue, Net Profit & EBITDA trends (topline vs bottomline scaling)
    2. Leverage & Cash Flow comparison (Debt vs FCF vs OCF)
    """
    years = metrics_data.get("years", [])
    metrics = metrics_data.get("metrics", {})
    if not years:
        return
        
    n_keep = 5
    years_plot = years[-n_keep:] if len(years) > n_keep else years
    
    # Create Columns for side-by-side charts
    col1, col2 = st.columns(2)
    
    # Chart 1: Revenue vs Net Profit vs EBITDA
    with col1:
        fig1 = go.Figure()
        
        rev = metrics.get("Revenue", [])
        net_prof = metrics.get("Net Profit", [])
        ebitda = metrics.get("EBITDA", [])
        
        rev_plot = rev[-n_keep:] if len(rev) > n_keep else rev
        ebitda_plot = ebitda[-n_keep:] if len(ebitda) > n_keep else ebitda
        net_prof_plot = net_prof[-n_keep:] if len(net_prof) > n_keep else net_prof
        
        if any(v is not None for v in rev_plot):
            fig1.add_trace(go.Scatter(
                x=years_plot, y=rev_plot, name="Revenue",
                line=dict(color="#3b82f6", width=3, shape="spline"),
                marker=dict(size=8)
            ))
        if any(v is not None for v in ebitda_plot):
            fig1.add_trace(go.Scatter(
                x=years_plot, y=ebitda_plot, name="EBITDA",
                line=dict(color="#8b5cf6", width=2.5, dash="dash", shape="spline"),
                marker=dict(size=6)
            ))
        if any(v is not None for v in net_prof_plot):
            fig1.add_trace(go.Scatter(
                x=years_plot, y=net_prof_plot, name="Net Profit",
                line=dict(color="#10b981", width=3, shape="spline"),
                marker=dict(size=8)
            ))
            
        fig1.update_layout(
            title="Earnings Scale & Profitability",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickmode="linear"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title="Value (₹ Cr)"),
            font=dict(color="rgba(255,255,255,0.7)"),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: Debt vs Operating Cash Flow vs Free Cash Flow
    with col2:
        fig2 = go.Figure()
        
        debt = metrics.get("Total Debt", [])
        ocf = metrics.get("Operating Cash Flow", [])
        fcf = metrics.get("Free Cash Flow", [])
        
        debt_plot = debt[-n_keep:] if len(debt) > n_keep else debt
        ocf_plot = ocf[-n_keep:] if len(ocf) > n_keep else ocf
        fcf_plot = fcf[-n_keep:] if len(fcf) > n_keep else fcf
        
        if any(v is not None for v in debt_plot):
            fig2.add_trace(go.Bar(
                x=years_plot, y=debt_plot, name="Total Debt",
                marker_color="rgba(239, 68, 68, 0.4)",
                marker_line=dict(color="#ef4444", width=1.5)
            ))
        if any(v is not None for v in ocf_plot):
            fig2.add_trace(go.Scatter(
                x=years_plot, y=ocf_plot, name="Operating CF",
                line=dict(color="#f59e0b", width=2.5, shape="spline"),
                marker=dict(size=6)
            ))
        if any(v is not None for v in fcf_plot):
            fig2.add_trace(go.Scatter(
                x=years_plot, y=fcf_plot, name="Free CF",
                line=dict(color="#06b6d4", width=2.5, shape="spline"),
                marker=dict(size=6)
            ))
            
        fig2.update_layout(
            title="Solvency & Cash Flow Generation",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickmode="linear"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title="Value (₹ Cr)"),
            font=dict(color="rgba(255,255,255,0.7)"),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig2, use_container_width=True)


def render_radar_chart(strength_data: Dict[str, Any]):
    """
    Renders a radar chart showing the Stock Strength Index breakdown normalized to 100%.
    """
    breakdown = strength_data.get("breakdown", {})
    if not breakdown:
        return
        
    category_max = {
        "Growth": 25,
        "Profitability": 20,
        "Cash Flow": 20,
        "Debt": 15,
        "Valuation": 10,
        "Capital Allocation": 10
    }
        
    categories = list(breakdown.keys())
    # Normalize values to 0-100% range
    values = []
    for cat in categories:
        max_val = category_max.get(cat, 20)
        val = breakdown[cat]
        pct = (val / max_val) * 100 if max_val > 0 else 0
        values.append(pct)
    
    # Close the radar loop
    categories.append(categories[0])
    values.append(values[0])
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        fillcolor='rgba(96, 165, 250, 0.25)',
        line=dict(color='#60a5fa', width=2),
        name='Score Breakdown (%)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                color="rgba(255,255,255,0.5)",
                gridcolor="rgba(255,255,255,0.05)",
                ticksuffix="%"
            ),
            angularaxis=dict(
                color="rgba(255,255,255,0.7)",
                gridcolor="rgba(255,255,255,0.05)"
            ),
            bgcolor="rgba(0,0,0,0)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="rgba(255,255,255,0.7)"),
        showlegend=False,
        title={
            'text': "Fundamental Strength Dimensions",
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        }
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_waterfall_chart(metrics_data: Dict[str, Any]):
    """
    Renders a waterfall bridge showing Cash Flow components for the latest year.
    It links Operating Cash Flow, Capex, and Free Cash Flow.
    """
    years = metrics_data.get("years", [])
    metrics = metrics_data.get("metrics", {})
    if not years:
        return
        
    latest_idx = -1
    latest_ocf = metrics.get("Operating Cash Flow", [None]*len(years))[latest_idx]
    latest_fcf = metrics.get("Free Cash Flow", [None]*len(years))[latest_idx]
    
    if latest_ocf is None or latest_fcf is None:
        # Fallback empty warning
        return
        
    # Capex is Operating Cash Flow - Free Cash Flow
    capex = latest_ocf - latest_fcf
    
    fig = go.Figure(go.Waterfall(
        name="Cash Flow",
        orientation="v",
        measure=["relative", "relative", "total"],
        x=["Operating Cash Flow", "Capital Expenditures", "Free Cash Flow"],
        textposition="outside",
        text=[f"{latest_ocf:+,.1f}", f"{-capex:+,.1f}", f"{latest_fcf:,.1f}"],
        y=[latest_ocf, -capex, latest_fcf],
        connector={"line": {"color": "rgba(255,255,255,0.15)", "width": 1.5}},
        decreasing={"marker": {"color": "rgba(239, 68, 68, 0.6)"}},
        increasing={"marker": {"color": "rgba(16, 185, 129, 0.6)"}},
        totals={"marker": {"color": "rgba(59, 130, 246, 0.6)"}}
    ))
    
    fig.update_layout(
        title="Cash Generation Bridge (Latest Year)",
        waterfallgap=0.3,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
        font=dict(color="rgba(255,255,255,0.7)"),
    )
    
    st.plotly_chart(fig, use_container_width=True)
