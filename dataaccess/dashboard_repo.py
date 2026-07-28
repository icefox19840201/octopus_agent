"""
仪表盘数据访问层
提供各类统计数据的数据库查询
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataaccess.models import (
    AgentModel, SkillModel, MCPModel, UserModel, 
    DepartmentModel, ChatMessageModel, AgentSkillMappingModel
)


class DashboardRepo:
    """仪表盘数据访问类"""

    @staticmethod
    def get_agent_stats(db: Session) -> Dict[str, Any]:
        """获取Agent统计数据"""
        total = db.query(func.count(AgentModel.agent_id)).scalar() or 0
        active = db.query(func.count(AgentModel.agent_id)).filter(
            AgentModel.status == 1
        ).scalar() or 0
        inactive = db.query(func.count(AgentModel.agent_id)).filter(
            AgentModel.status == 0
        ).scalar() or 0
        
        # 按可见性统计
        public = db.query(func.count(AgentModel.agent_id)).filter(
            AgentModel.type == 'public'
        ).scalar() or 0
        private = db.query(func.count(AgentModel.agent_id)).filter(
            AgentModel.type == 'private'
        ).scalar() or 0
        group = db.query(func.count(AgentModel.agent_id)).filter(
            AgentModel.type == 'group'
        ).scalar() or 0
        
        # 今日新增
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = db.query(func.count(AgentModel.agent_id)).filter(
            AgentModel.created_at >= today
        ).scalar() or 0
        
        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "public": public,
            "private": private,
            "group": group,
            "today_count": today_count
        }

    @staticmethod
    def get_skill_stats(db: Session) -> Dict[str, Any]:
        """获取Skill统计数据"""
        total = db.query(func.count(SkillModel.id)).scalar() or 0
        
        # 按可见性统计
        public = db.query(func.count(SkillModel.id)).filter(
            SkillModel.type == 'public'
        ).scalar() or 0
        private = db.query(func.count(SkillModel.id)).filter(
            SkillModel.type == 'private'
        ).scalar() or 0
        group = db.query(func.count(SkillModel.id)).filter(
            SkillModel.type == 'group'
        ).scalar() or 0
        
        # 今日新增
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = db.query(func.count(SkillModel.id)).filter(
            SkillModel.created_at >= today
        ).scalar() or 0
        
        return {
            "total": total,
            "public": public,
            "private": private,
            "group": group,
            "today_count": today_count
        }

    @staticmethod
    def get_mcp_stats(db: Session) -> Dict[str, Any]:
        """获取MCP服务统计数据"""
        total = db.query(func.count(MCPModel.id)).scalar() or 0
        
        # 按状态统计
        active = db.query(func.count(MCPModel.id)).filter(
            MCPModel.status == 'active'
        ).scalar() or 0
        stopped = db.query(func.count(MCPModel.id)).filter(
            MCPModel.status == 'stopped'
        ).scalar() or 0
        
        # 按可见性统计
        public = db.query(func.count(MCPModel.id)).filter(
            MCPModel.visibility == 'public'
        ).scalar() or 0
        private = db.query(func.count(MCPModel.id)).filter(
            MCPModel.visibility == 'private'
        ).scalar() or 0
        group = db.query(func.count(MCPModel.id)).filter(
            MCPModel.visibility == 'group'
        ).scalar() or 0
        
        # 按类型统计
        sse = db.query(func.count(MCPModel.id)).filter(
            MCPModel.type == 'sse'
        ).scalar() or 0
        stdio = db.query(func.count(MCPModel.id)).filter(
            MCPModel.type == 'stdio'
        ).scalar() or 0
        http = db.query(func.count(MCPModel.id)).filter(
            MCPModel.type == 'streamable-http'
        ).scalar() or 0
        
        # 今日新增
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = db.query(func.count(MCPModel.id)).filter(
            MCPModel.created_at >= today
        ).scalar() or 0
        
        return {
            "total": total,
            "active": active,
            "stopped": stopped,
            "public": public,
            "private": private,
            "group": group,
            "sse": sse,
            "stdio": stdio,
            "http": http,
            "today_count": today_count
        }

    @staticmethod
    def get_user_stats(db: Session) -> Dict[str, Any]:
        """获取用户统计数据"""
        total = db.query(func.count(UserModel.id)).scalar() or 0
        
        # 按状态统计
        active = db.query(func.count(UserModel.id)).filter(
            UserModel.status == 'active'
        ).scalar() or 0
        inactive = db.query(func.count(UserModel.id)).filter(
            UserModel.status == 'inactive'
        ).scalar() or 0
        
        # 今日新增
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = db.query(func.count(UserModel.id)).filter(
            UserModel.created_at >= today
        ).scalar() or 0
        
        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "today_count": today_count
        }

    @staticmethod
    def get_department_stats(db: Session) -> Dict[str, Any]:
        """获取部门统计数据"""
        total = db.query(func.count(DepartmentModel.id)).scalar() or 0
        
        # 按状态统计
        active = db.query(func.count(DepartmentModel.id)).filter(
            DepartmentModel.status == 'active'
        ).scalar() or 0
        inactive = db.query(func.count(DepartmentModel.id)).filter(
            DepartmentModel.status == 'inactive'
        ).scalar() or 0
        
        return {
            "total": total,
            "active": active,
            "inactive": inactive
        }

    @staticmethod
    def get_chat_stats(db: Session) -> Dict[str, Any]:
        """获取对话统计数据"""
        total = db.query(func.count(ChatMessageModel.id)).scalar() or 0
        
        # 今日对话数
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = db.query(func.count(ChatMessageModel.id)).filter(
            ChatMessageModel.created_at >= today
        ).scalar() or 0
        
        # 本周对话数
        week_start = today - timedelta(days=today.weekday())
        week_count = db.query(func.count(ChatMessageModel.id)).filter(
            ChatMessageModel.created_at >= week_start
        ).scalar() or 0
        
        # 本月对话数
        month_start = today.replace(day=1)
        month_count = db.query(func.count(ChatMessageModel.id)).filter(
            ChatMessageModel.created_at >= month_start
        ).scalar() or 0
        
        # 独立会话数
        conversation_count = db.query(func.count(
            func.distinct(ChatMessageModel.conversation_id)
        )).scalar() or 0
        
        return {
            "total": total,
            "today_count": today_count,
            "week_count": week_count,
            "month_count": month_count,
            "conversation_count": conversation_count
        }

    @staticmethod
    def get_recent_activities(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的活动记录"""
        activities = []
        
        # 最近创建的Agent
        recent_agents = db.query(AgentModel).order_by(
            desc(AgentModel.created_at)
        ).limit(limit).all()
        
        for agent in recent_agents:
            activities.append({
                "type": "agent_created",
                "title": f"创建智能体: {agent.name}",
                "time": agent.created_at.isoformat() if agent.created_at else None,
                "user_id": agent.created_by
            })
        
        # 最近创建的Skill
        recent_skills = db.query(SkillModel).order_by(
            desc(SkillModel.created_at)
        ).limit(limit).all()
        
        for skill in recent_skills:
            activities.append({
                "type": "skill_created",
                "title": f"创建技能: {skill.skills_name}",
                "time": skill.created_at.isoformat() if skill.created_at else None,
                "user_id": skill.created_by
            })
        
        # 按时间排序
        activities.sort(key=lambda x: x["time"] or "", reverse=True)
        return activities[:limit]

    @staticmethod
    def get_agent_skill_mapping_stats(db: Session) -> Dict[str, Any]:
        """获取Agent与Skill关联统计"""
        total_mappings = db.query(func.count(AgentSkillMappingModel.id)).scalar() or 0
        
        # 平均每个Agent绑定的Skill数量
        agent_count = db.query(func.count(AgentModel.agent_id)).scalar() or 1
        avg_skills_per_agent = round(total_mappings / agent_count, 2)
        
        # 被使用最多的Skill
        top_skills = db.query(
            AgentSkillMappingModel.skills_id,
            func.count(AgentSkillMappingModel.id).label('usage_count')
        ).group_by(
            AgentSkillMappingModel.skills_id
        ).order_by(
            desc('usage_count')
        ).limit(5).all()
        
        return {
            "total_mappings": total_mappings,
            "avg_skills_per_agent": avg_skills_per_agent,
            "top_skills": [
                {"skill_id": skill_id, "usage_count": count}
                for skill_id, count in top_skills
            ]
        }

    @staticmethod
    def get_popular_agents(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
        """获取热门Agent（按对话消息数统计）"""
        from dataaccess.models import ChatMessageModel
        
        popular = db.query(
            AgentModel.agent_id,
            AgentModel.name,
            func.count(ChatMessageModel.id).label('message_count')
        ).outerjoin(
            ChatMessageModel, AgentModel.agent_id == ChatMessageModel.agent_id
        ).group_by(
            AgentModel.agent_id, AgentModel.name
        ).order_by(
            desc('message_count')
        ).limit(limit).all()
        
        return [
            {
                "agent_id": agent_id,
                "name": name,
                "message_count": message_count or 0
            }
            for agent_id, name, message_count in popular
        ]

    @staticmethod
    def get_popular_skills(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
        """获取热门Skill（按绑定Agent数量统计）"""
        popular = db.query(
            SkillModel.id,
            SkillModel.skills_name,
            func.count(AgentSkillMappingModel.id).label('agent_count')
        ).outerjoin(
            AgentSkillMappingModel, SkillModel.id == AgentSkillMappingModel.skills_id
        ).group_by(
            SkillModel.id, SkillModel.skills_name
        ).order_by(
            desc('agent_count')
        ).limit(limit).all()
        
        return [
            {
                "skill_id": skill_id,
                "name": skills_name,
                "agent_count": agent_count or 0
            }
            for skill_id, skills_name, agent_count in popular
        ]

    @staticmethod
    def get_popular_mcps(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
        """获取热门MCP（按使用频率统计，这里用创建时间最近的代替）"""
        popular = db.query(
            MCPModel.id,
            MCPModel.name,
            MCPModel.created_at
        ).order_by(
            desc(MCPModel.created_at)
        ).limit(limit).all()
        
        return [
            {
                "mcp_id": mcp_id,
                "name": name,
                "created_at": created_at.isoformat() if created_at else None
            }
            for mcp_id, name, created_at in popular
        ]

    @staticmethod
    def get_daily_stats(db: Session, days: int = 7) -> List[Dict[str, Any]]:
        """获取按天统计的数据（用于折线图）"""
        from dataaccess.models import ChatMessageModel
        
        result = []
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(days - 1, -1, -1):
            day = today - timedelta(days=i)
            next_day = day + timedelta(days=1)
            
            # 该天的新增Agent数
            new_agents = db.query(func.count(AgentModel.agent_id)).filter(
                AgentModel.created_at >= day,
                AgentModel.created_at < next_day
            ).scalar() or 0
            
            # 该天的新增Skill数
            new_skills = db.query(func.count(SkillModel.id)).filter(
                SkillModel.created_at >= day,
                SkillModel.created_at < next_day
            ).scalar() or 0
            
            # 该天的对话消息数
            chat_count = db.query(func.count(ChatMessageModel.id)).filter(
                ChatMessageModel.created_at >= day,
                ChatMessageModel.created_at < next_day
            ).scalar() or 0
            
            # 该天的新增用户数
            new_users = db.query(func.count(UserModel.id)).filter(
                UserModel.created_at >= day,
                UserModel.created_at < next_day
            ).scalar() or 0
            
            result.append({
                "date": day.strftime("%m-%d"),
                "new_agents": new_agents,
                "new_skills": new_skills,
                "chat_count": chat_count,
                "new_users": new_users
            })
        
        return result
