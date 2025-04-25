from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from database import get_db, engine
import models
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Tradeverse API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Pydantic models
class UserCreate(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool

class TradeCreate(BaseModel):
    asset: str
    entry_price: float
    exit_price: float
    position_size: float
    entry_date: str
    exit_date: str
    direction: str
    strategy: str | None = None
    screenshot_path: str | None = None
    notes: str | None = None

class TradeResponse(BaseModel):
    id: int
    asset: str
    entry_price: float
    exit_price: float
    position_size: float
    entry_date: str
    exit_date: str
    direction: str
    strategy: str | None = None
    screenshot_path: str | None = None
    notes: str | None = None
    created_at: str
    owner_id: int

    class Config:
        from_attributes = True

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# Routes
@app.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/trades", response_model=TradeResponse)
def create_trade(trade: TradeCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        # Convert string dates to datetime objects
        entry_date = datetime.fromisoformat(trade.entry_date)
        exit_date = datetime.fromisoformat(trade.exit_date)
        
        db_trade = models.Trade(
            asset=trade.asset,
            entry_price=trade.entry_price,
            exit_price=trade.exit_price,
            position_size=trade.position_size,
            entry_date=entry_date,
            exit_date=exit_date,
            direction=trade.direction,
            strategy=trade.strategy,
            screenshot_path=trade.screenshot_path,
            notes=trade.notes,
            owner_id=current_user.id
        )
        db.add(db_trade)
        db.commit()
        db.refresh(db_trade)
        
        # Convert back to string for response
        trade_dict = {
            "id": db_trade.id,
            "asset": db_trade.asset,
            "entry_price": db_trade.entry_price,
            "exit_price": db_trade.exit_price,
            "position_size": db_trade.position_size,
            "entry_date": db_trade.entry_date.isoformat(),
            "exit_date": db_trade.exit_date.isoformat(),
            "direction": db_trade.direction,
            "strategy": db_trade.strategy,
            "screenshot_path": db_trade.screenshot_path,
            "notes": db_trade.notes,
            "created_at": db_trade.created_at.isoformat(),
            "owner_id": db_trade.owner_id
        }
        return trade_dict
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/trades", response_model=List[TradeResponse])
def read_trades(skip: int = 0, limit: int = 100, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        trades = db.query(models.Trade).filter(models.Trade.owner_id == current_user.id).offset(skip).limit(limit).all()
        
        trade_list = []
        for trade in trades:
            trade_dict = {
                "id": trade.id,
                "asset": trade.asset,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "position_size": trade.position_size,
                "entry_date": trade.entry_date.isoformat(),
                "exit_date": trade.exit_date.isoformat(),
                "direction": trade.direction,
                "strategy": trade.strategy,
                "screenshot_path": trade.screenshot_path,
                "notes": trade.notes,
                "created_at": trade.created_at.isoformat(),
                "owner_id": trade.owner_id
            }
            trade_list.append(trade_dict)
        
        return trade_list
    except Exception as e:
        print(f"Error fetching trades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/trades/{trade_id}", response_model=TradeResponse)
def update_trade(trade_id: int, trade: TradeCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        db_trade = db.query(models.Trade).filter(
            models.Trade.id == trade_id,
            models.Trade.owner_id == current_user.id
        ).first()
        
        if not db_trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        # Convert string dates to datetime objects
        entry_date = datetime.fromisoformat(trade.entry_date)
        exit_date = datetime.fromisoformat(trade.exit_date)
        
        # Update trade fields
        for field, value in trade.dict().items():
            if field not in ['entry_date', 'exit_date']:
                setattr(db_trade, field, value)
        
        db_trade.entry_date = entry_date
        db_trade.exit_date = exit_date
        
        db.commit()
        db.refresh(db_trade)
        
        # Convert back to string for response
        trade_dict = {
            "id": db_trade.id,
            "asset": db_trade.asset,
            "entry_price": db_trade.entry_price,
            "exit_price": db_trade.exit_price,
            "position_size": db_trade.position_size,
            "entry_date": db_trade.entry_date.isoformat(),
            "exit_date": db_trade.exit_date.isoformat(),
            "direction": db_trade.direction,
            "strategy": db_trade.strategy,
            "screenshot_path": db_trade.screenshot_path,
            "notes": db_trade.notes,
            "created_at": db_trade.created_at.isoformat(),
            "owner_id": db_trade.owner_id
        }
        return trade_dict
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/trades/{trade_id}")
def delete_trade(trade_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        db_trade = db.query(models.Trade).filter(
            models.Trade.id == trade_id,
            models.Trade.owner_id == current_user.id
        ).first()
        
        if not db_trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        db.delete(db_trade)
        db.commit()
        return {"message": "Trade deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# Create database tables
models.Base.metadata.create_all(bind=engine) 