from pydantic import BaseModel, ConfigDict, Field


class AgentSkillBase(BaseModel):
    agent_id: int = Field(..., gt=0)
    category_id: int = Field(..., gt=0)
    proficiency: int = Field(default=3, ge=1, le=5)


class AgentSkillCreate(AgentSkillBase):
    pass


class AgentSkillUpdate(BaseModel):
    proficiency: int = Field(..., ge=1, le=5)


class AgentSkillResponse(AgentSkillBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
