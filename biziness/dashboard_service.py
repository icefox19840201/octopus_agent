"""
仪表盘业务逻辑层
处理仪表盘数据的业务逻辑和组装
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from dataaccess.dashboard_repo import DashboardRepo
from utils.logger import logger


class DashboardService:
    """仪表盘业务服务类"""

    @staticmethod
    def get_overview_stats(db: Session) -> Dict[str, Any]:
        """获取概览统计数据"""
        try:
            agent_stats = DashboardRepo.get_agent_stats(db)
            skill_stats = DashboardRepo.get_skill_stats(db)
            mcp_stats = DashboardRepo.get_mcp_stats(db)
            user_stats = DashboardRepo.get_user_stats(db)
            chat_stats = DashboardRepo.get_chat_stats(db)
            dept_stats = DashboardRepo.get_department_stats(db)
            
            return {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "agents": {
                        "total": agent_stats["total"],
                        "active": agent_stats["active"],
                        "today_count": agent_stats["today_count"]
                    },
                    "skills": {
                        "total": skill_stats["total"],
                        "today_count": skill_stats["today_count"]
                    },
                    "mcps": {
                        "total": mcp_stats["total"],
                        "active": mcp_stats["active"],
                        "today_count": mcp_stats["today_count"]
                    },
                    "users": {
                        "total": user_stats["total"],
                        "active": user_stats["active"],
                        "today_count": user_stats["today_count"]
                    },
                    "chats": {
                        "total": chat_stats["total"],
                        "today_count": chat_stats["today_count"],
                        "conversation_count": chat_stats["conversation_count"]
                    },
                    "departments": {
                        "total": dept_stats["total"],
                        "active": dept_stats["active"]
                    }
                }
            }
        except Exception as e:
            logger.exception(f"获取概览统计数据失败: {e}")
            return {
                "code": 500,
                "message": f"获取统计数据失败: {str(e)}"
            }

    @staticmethod
    def get_agent_detail_stats(db: Session) -> Dict[str, Any]:
        """获取Agent详细统计"""
        try:
            stats = DashboardRepo.get_agent_stats(db)
            mapping_stats = DashboardRepo.get_agent_skill_mapping_stats(db)
            
            return {
                "code": 200,
                "message": "获取成功",
                "data": {
                    **stats,
                    **mapping_stats
                }
            }
        except Exception as e:
            logger.exception(f"获取Agent详细统计失败: {e}")
            return {
                "code": 500,
                "message": f"获取失败: {str(e)}"
            }

    @staticmethod
    def get_skill_detail_stats(db: Session) -> Dict[str, Any]:
        """获取Skill详细统计"""
        try:
            stats = DashboardRepo.get_skill_stats(db)
            mapping_stats = DashboardRepo.get_agent_skill_mapping_stats(db)
            
            return {
                "code": 200,
                "message": "获取成功",
                "data": {
                    **stats,
                    **mapping_stats
                }
            }
        except Exception as e:
            logger.exception(f"获取Skill详细统计失败: {e}")
            return {
                "code": 500,
                "message": f"获取失败: {str(e)}"
            }

    @staticmethod
    def get_mcp_detail_stats(db: Session) -> Dict[str, Any]:
        """获取MCP详细统计"""
        try:
            stats = DashboardRepo.get_mcp_stats(db)
            
            return {
                "code": 200,
                "message": "获取成功",
                "data": stats
            }
        except Exception as e:
            logger.exception(f"获取MCP详细统计失败: {e}")
            return {
                "code": 500,
                "message": f"获取失败: {str(e)}"
            }

    @staticmethod
    def get_chat_detail_stats(db: Session) -> Dict[str, Any]:
        """获取对话详细统计"""
        try:
            stats = DashboardRepo.get_chat_stats(db)
            
            return {
                "code": 200,
                "message": "获取成功",
                "data": stats
            }
        except Exception as e:
            logger.exception(f"获取对话详细统计失败: {e}")
            return {
                "code": 500,
                "message": f"获取失败: {str(e)}"
            }

    @staticmethod
    def get_recent_activities(db: Session, limit: int = 10) -> Dict[str, Any]:
        """获取最近活动"""
        try:
            activities = DashboardRepo.get_recent_activities(db, limit)
            
            return {
                "code": 200,
                "message": "获取成功",
                "data": activities
            }
        except Exception as e:
            logger.exception(f"获取最近活动失败: {e}")
            return {
                "code": 500,
                "message": f"获取失败: {str(e)}"
            }

    @staticmethod
    def get_full_dashboard_data(db: Session) -> Dict[str, Any]:
        """获取完整的仪表盘数据"""
        try:
            overview = DashboardService.get_overview_stats(db)
            recent_activities = DashboardService.get_recent_activities(db, 10)
            
            if overview["code"] != 200:
                return overview
            
            if recent_activities["code"] != 200:
                recent_activities["data"] = []
            
            return {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "overview": overview["data"],
                    "recent_activities": recent_activities["data"]
                }
            }
        except Exception as e:
            logger.exception(f"获取仪表盘数据失败: {e}")
            return {
                "code": 500,
                "message": f"获取失败: {str(e)}"
            }

    @staticmethod
    def get_popular_data(db: Session) -> Dict[str, Any]:
        """获取热门数据（Agent、Skill、MCP排行榜）"""
        try:
            popular_agents = DashboardRepo.get_popular_agents(db, 5)
            popular_skills = DashboardRepo.get_popular_skills(db, 5)
            popular_mcps = DashboardRepo.get_popular_mcps(db, 5)
            
            return {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "popular_agents": popular_agents,
                    "popular_skills": popular_skills,
                    "popular_mcps": popular_mcps
                }
            }
        except Exception as e:
            logger.exception(f"获取热门数据失败: {e}")
            return {
                "code": 500,
                "message": f"获取失败: {str(e)}"
            }

    @staticmethod
    def get_daily_stats(db: Session, days: int = 7) -> Dict[str, Any]:
        """获取按天统计数据"""
        try:
            daily_stats = DashboardRepo.get_daily_stats(db, days)
            
            return {
                "code": 200,
                "message": "获取成功",
                "data": daily_stats
            }
        except Exception as e:
            logger.exception(f"获取按天统计失败: {e}")
            return {
                "code": 500,
                "message": f"获取失败: {str(e)}"
            }

    @staticmethod
    def get_complete_dashboard(db: Session) -> Dict[str, Any]:
        """获取完整的仪表盘数据（包含所有统计）"""
        try:
            overview = DashboardService.get_overview_stats(db)
            recent_activities = DashboardService.get_recent_activities(db, 10)
            popular_data = DashboardService.get_popular_data(db)
            daily_stats = DashboardService.get_daily_stats(db, 7)
            
            if overview["code"] != 200:
                return overview
            
            return {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "overview": overview["data"],
                    "recent_activities": recent_activities.get("data", []),
                    "popular": popular_data.get("data", {}),
                    "daily_stats": daily_stats.get("data", [])
                }
            }
        except Exception as e:
            logger.exception(f"获取完整仪表盘数据失败: {e}")
            return {
                "code": 500,
                "message": f"获取失败: {str(e)}"
            }
