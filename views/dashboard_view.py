"""
仪表盘视图层
提供仪表盘相关的API接口
"""
from fastapi import Request, Depends
from sqlalchemy.orm import Session
from dataaccess.database import get_db
from biziness.dashboard_service import DashboardService
from utils.auth_decorator import require_auth


@require_auth
async def get_dashboard_overview(request: Request, db: Session = Depends(get_db)):
    """
    获取仪表盘概览数据
    包含Agent、Skill、MCP、用户、对话、部门的核心统计数据
    """
    return DashboardService.get_overview_stats(db)


@require_auth
async def get_dashboard_full(request: Request, db: Session = Depends(get_db)):
    """
    获取完整的仪表盘数据
    包含概览统计和最近活动记录
    """
    return DashboardService.get_full_dashboard_data(db)


@require_auth
async def get_agent_stats(request: Request, db: Session = Depends(get_db)):
    """
    获取Agent详细统计数据
    """
    return DashboardService.get_agent_detail_stats(db)


@require_auth
async def get_skill_stats(request: Request, db: Session = Depends(get_db)):
    """
    获取Skill详细统计数据
    """
    return DashboardService.get_skill_detail_stats(db)


@require_auth
async def get_mcp_stats(request: Request, db: Session = Depends(get_db)):
    """
    获取MCP服务详细统计数据
    """
    return DashboardService.get_mcp_detail_stats(db)


@require_auth
async def get_chat_stats(request: Request, db: Session = Depends(get_db)):
    """
    获取对话详细统计数据
    """
    return DashboardService.get_chat_detail_stats(db)


@require_auth
async def get_recent_activities(request: Request, limit: int = 10, db: Session = Depends(get_db)):
    """
    获取最近活动记录
    
    参数:
        limit: 返回记录数量，默认10条
    """
    return DashboardService.get_recent_activities(db, limit)


@require_auth
async def get_popular_stats(request: Request, db: Session = Depends(get_db)):
    """
    获取热门排行榜数据
    包含热门Agent、Skill、MCP的排行
    """
    return DashboardService.get_popular_data(db)


@require_auth
async def get_daily_trend(request: Request, days: int = 7, db: Session = Depends(get_db)):
    """
    获取按天趋势数据
    
    参数:
        days: 天数，默认7天
    """
    return DashboardService.get_daily_stats(db, days)


@require_auth
async def get_dashboard_complete(request: Request, db: Session = Depends(get_db)):
    """
    获取完整的仪表盘数据
    包含概览统计、最近活动、热门排行榜和趋势数据
    """
    return DashboardService.get_complete_dashboard(db)
