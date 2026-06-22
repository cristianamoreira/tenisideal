# No Rats — Frontend Implementation Guide

## 0. Scaffold Inicial

### 0.1 Setup com Vite

```bash
# Criar projeto Vite
npm create vite@latest no-rats-frontend -- --template react-ts

cd no-rats-frontend

# Instalar dependências
npm install

# Instalar Tailwind + shadcn/ui
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-slot
npm install class-variance-authority clsx tailwind-merge
npm install -D @types/node

# shadcn/ui CLI
npm install -D shadcn-ui
npx shadcn-ui@latest init -d

# Outras dependências
npm install react-router-dom axios zustand react-hook-form zod
npm install date-fns
```

### 0.2 Estrutura de Pastas

```
no-rats-frontend/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── index.css
│   ├── api/
│   │   └── client.ts
│   ├── components/
│   │   ├── ui/ (shadcn/ui gerados)
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── form.tsx
│   │   │   ├── checkbox.tsx
│   │   │   ├── radio-group.tsx
│   │   │   └── select.tsx
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   └── MainLayout.tsx
│   │   └── common/
│   │       ├── InfestationIndicator.tsx
│   │       └── XPBar.tsx
│   ├── context/
│   │   ├── AuthContext.tsx
│   │   ├── GameContext.tsx
│   │   └── TaskContext.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useGame.ts
│   │   └── useApi.ts
│   ├── pages/
│   │   ├── auth/
│   │   │   ├── Login.tsx
│   │   │   └── Register.tsx
│   │   ├── onboarding/
│   │   │   └── Onboarding.tsx
│   │   ├── dashboard/
│   │   │   └── Dashboard.tsx
│   │   ├── tasks/
│   │   │   ├── TaskList.tsx
│   │   │   ├── CreateTask.tsx
│   │   │   └── EditTask.tsx
│   │   └── NotFound.tsx
│   ├── services/
│   │   ├── authService.ts
│   │   ├── taskService.ts
│   │   ├── roomService.ts
│   │   └── types.ts
│   ├── types/
│   │   └── index.ts
│   ├── utils/
│   │   ├── storage.ts
│   │   └── constants.ts
│   └── lib/
│       └── utils.ts
├── public/
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## 1. TypeScript Types

### `src/types/index.ts`

```typescript
// User & Auth
export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  total_xp: number;
  level: number;
  level_xp: number;
  streak: number;
  total_infestation: number;
  xp_for_next_level: number;
  created_at: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

// Room
export interface Room {
  id: string;
  name: string;
  room_name: string; // Display name
  infestation: number; // 0-100
  created_at: string;
}

export const ROOM_NAMES: Record<string, string> = {
  cozinha: 'Cozinha',
  banheiro: 'Banheiro',
  quarto: 'Quarto',
  sala: 'Sala',
  lavanderia: 'Lavanderia',
  escritorio: 'Escritório',
};

// Task
export interface Task {
  id: string;
  room: string;
  room_name: string;
  title: string;
  description?: string;
  category?: string;
  difficulty: 'simples' | 'media' | 'dificil' | 'pesada';
  difficulty_display: string;
  frequency: 'diaria' | 'semanal' | 'quinzenal' | 'mensal';
  frequency_display: string;
  due_date: string;
  status: 'pendente' | 'concluida' | 'vencida';
  status_display: string;
  xp_value: number;
  recurring: boolean;
  completed_at?: string;
  is_overdue: boolean;
  created_at: string;
}

export interface CreateTaskInput {
  room: string;
  title: string;
  description?: string;
  category?: string;
  difficulty: 'simples' | 'media' | 'dificil' | 'pesada';
  frequency: 'diaria' | 'semanal' | 'quinzenal' | 'mensal';
}

export interface TaskCompletion {
  id: string;
  task: string;
  task_title: string;
  room: string;
  room_name: string;
  xp_earned: number;
  streak_maintained: boolean;
  infestation_cleared: number;
  level_before: number;
  level_after: number;
  completed_at: string;
}

// Game State
export interface GameState {
  user: User | null;
  rooms: Room[];
  tasks: Task[];
  completions: TaskCompletion[];
  loading: boolean;
  error: string | null;
}

// API Response
export interface ApiResponse<T> {
  data: T;
  status: number;
}

export interface ApiError {
  error: string;
  status: number;
}
```

---

## 2. API Client & Services

### `src/api/client.ts`

```typescript
import axios, { AxiosInstance, AxiosError } from 'axios';
import { User, AuthTokens } from '../types';
import { getStoredToken, setStoredToken, clearStoredToken } from '../utils/storage';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add token to requests
    this.client.interceptors.request.use((config) => {
      const token = getStoredToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token.access}`;
      }
      return config;
    });

    // Handle 401 and refresh token
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as any;
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          try {
            const token = getStoredToken();
            if (token?.refresh) {
              const response = await axios.post(`${API_URL}/auth/token/refresh/`, {
                refresh: token.refresh,
              });
              setStoredToken(response.data);
              return this.client(originalRequest);
            }
          } catch {
            clearStoredToken();
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );
  }

  get<T>(url: string) {
    return this.client.get<T>(url);
  }

  post<T>(url: string, data?: any) {
    return this.client.post<T>(url, data);
  }

  put<T>(url: string, data?: any) {
    return this.client.put<T>(url, data);
  }

  patch<T>(url: string, data?: any) {
    return this.client.patch<T>(url, data);
  }

  delete<T>(url: string) {
    return this.client.delete<T>(url);
  }
}

export const apiClient = new ApiClient();
```

### `src/services/authService.ts`

```typescript
import { apiClient } from '../api/client';
import { User, AuthTokens, AuthResponse } from '../types';
import { setStoredToken, getStoredToken } from '../utils/storage';

export const authService = {
  async register(email: string, name: string, password: string): Promise<User> {
    const response = await apiClient.post<User>('/auth/users/register/', {
      email,
      name,
      password,
      password_confirm: password,
    });
    return response.data;
  },

  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await apiClient.post<AuthTokens>('/auth/token/', {
      email,
      password,
    });
    setStoredToken(response.data);
    
    // Fetch user data
    const userResponse = await apiClient.get<User>('/auth/users/me/');
    return {
      user: userResponse.data,
      tokens: response.data,
    };
  },

  async getMe(): Promise<User> {
    const response = await apiClient.get<User>('/auth/users/me/');
    return response.data;
  },

  async updateProfile(name: string, avatar_url?: string): Promise<User> {
    const response = await apiClient.put<User>('/auth/users/update_profile/', {
      name,
      avatar_url,
    });
    return response.data;
  },

  logout() {
    setStoredToken(null);
  },

  isAuthenticated(): boolean {
    return !!getStoredToken();
  },
};
```

### `src/services/roomService.ts`

```typescript
import { apiClient } from '../api/client';
import { Room } from '../types';

export const roomService = {
  async list(): Promise<Room[]> {
    const response = await apiClient.get<Room[]>('/houses/rooms/');
    return response.data;
  },

  async create(name: string): Promise<Room> {
    const response = await apiClient.post<Room>('/houses/rooms/', { name });
    return response.data;
  },

  async setupHouse(rooms: string[]): Promise<Room[]> {
    const response = await apiClient.post<Room[]>('/houses/rooms/setup_house/', {
      rooms,
    });
    return response.data;
  },

  async getRoomInfestationHistory(roomId: string) {
    const response = await apiClient.get(`/houses/room-events/?room=${roomId}`);
    return response.data;
  },
};
```

### `src/services/taskService.ts`

```typescript
import { apiClient } from '../api/client';
import { Task, TaskCompletion, CreateTaskInput } from '../types';

export const taskService = {
  async list(): Promise<Task[]> {
    const response = await apiClient.get<Task[]>('/tasks/tasks/');
    return response.data;
  },

  async pending(): Promise<Task[]> {
    const response = await apiClient.get<Task[]>('/tasks/tasks/pending/');
    return response.data;
  },

  async completed(): Promise<Task[]> {
    const response = await apiClient.get<Task[]>('/tasks/tasks/completed/');
    return response.data;
  },

  async create(input: CreateTaskInput): Promise<Task> {
    // Calcular due_date baseado em frequência
    const now = new Date();
    let dueDate = new Date(now);
    
    switch (input.frequency) {
      case 'diaria':
        dueDate.setDate(dueDate.getDate() + 1);
        dueDate.setHours(23, 59, 59);
        break;
      case 'semanal':
        dueDate.setDate(dueDate.getDate() + 7);
        break;
      case 'quinzenal':
        dueDate.setDate(dueDate.getDate() + 14);
        break;
      case 'mensal':
        dueDate.setDate(dueDate.getDate() + 30);
        break;
    }

    const response = await apiClient.post<Task>('/tasks/tasks/', {
      ...input,
      due_date: dueDate.toISOString(),
    });
    return response.data;
  },

  async update(id: string, input: Partial<CreateTaskInput>): Promise<Task> {
    const response = await apiClient.patch<Task>(`/tasks/tasks/${id}/`, input);
    return response.data;
  },

  async delete(id: string): Promise<void> {
    await apiClient.delete(`/tasks/tasks/${id}/`);
  },

  async complete(id: string) {
    const response = await apiClient.post(`/tasks/tasks/${id}/complete/`);
    return response.data;
  },
};
```

---

## 3. Context & State Management

### `src/context/AuthContext.tsx`

```typescript
import React, { createContext, useCallback, useEffect, useState } from 'react';
import { User, AuthTokens } from '../types';
import { authService } from '../services/authService';
import { getStoredToken, setStoredToken } from '../utils/storage';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string) => Promise<void>;
  logout: () => void;
  updateProfile: (name: string, avatar_url?: string) => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Initialize auth state from storage
  useEffect(() => {
    const initAuth = async () => {
      try {
        if (authService.isAuthenticated()) {
          const userData = await authService.getMe();
          setUser(userData);
        }
      } catch (error) {
        console.error('Failed to initialize auth:', error);
        authService.logout();
      } finally {
        setLoading(false);
      }
    };
    initAuth();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    try {
      const { user } = await authService.login(email, password);
      setUser(user);
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (email: string, name: string, password: string) => {
    setLoading(true);
    try {
      await authService.register(email, name, password);
      // Após registrar, fazer login automático
      await login(email, password);
    } finally {
      setLoading(false);
    }
  }, [login]);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  const updateProfile = useCallback(async (name: string, avatar_url?: string) => {
    setLoading(true);
    try {
      const updated = await authService.updateProfile(name, avatar_url);
      setUser(updated);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        loading,
        login,
        register,
        logout,
        updateProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
```

### `src/context/GameContext.tsx`

```typescript
import React, { createContext, useCallback, useEffect, useState } from 'react';
import { User, Room, Task, TaskCompletion } from '../types';
import { taskService } from '../services/taskService';
import { roomService } from '../services/roomService';

interface GameContextType {
  rooms: Room[];
  tasks: Task[];
  completions: TaskCompletion[];
  loading: boolean;
  error: string | null;
  refreshRooms: () => Promise<void>;
  refreshTasks: () => Promise<void>;
  completeTask: (taskId: string) => Promise<TaskCompletion | null>;
}

export const GameContext = createContext<GameContextType | undefined>(undefined);

export const GameProvider: React.FC<{ children: React.ReactNode; user: User | null }> = ({
  children,
  user,
}) => {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [completions, setCompletions] = useState<TaskCompletion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshRooms = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const data = await roomService.list();
      setRooms(data);
      setError(null);
    } catch (err) {
      setError('Erro ao carregar cômodos');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [user]);

  const refreshTasks = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const data = await taskService.list();
      setTasks(data);
      setError(null);
    } catch (err) {
      setError('Erro ao carregar tarefas');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [user]);

  const completeTask = useCallback(
    async (taskId: string) => {
      try {
        const result = await taskService.complete(taskId);
        const completion: TaskCompletion = result.completion;

        // Update user context (com novo XP, nível, etc)
        // Isso dispara update em AuthContext

        // Update task no local (marcando como concluída)
        setTasks((prev) =>
          prev.map((t) =>
            t.id === taskId ? { ...t, status: 'concluida' as const } : t
          )
        );

        // Refresh rooms pra atualizar infestação
        await refreshRooms();

        return completion;
      } catch (err) {
        setError('Erro ao completar tarefa');
        console.error(err);
        return null;
      }
    },
    [refreshRooms]
  );

  // Carrega dados quando usuário muda
  useEffect(() => {
    if (user) {
      refreshRooms();
      refreshTasks();
    }
  }, [user, refreshRooms, refreshTasks]);

  return (
    <GameContext.Provider
      value={{
        rooms,
        tasks,
        completions,
        loading,
        error,
        refreshRooms,
        refreshTasks,
        completeTask,
      }}
    >
      {children}
    </GameContext.Provider>
  );
};
```

---

## 4. Custom Hooks

### `src/hooks/useAuth.ts`

```typescript
import { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

### `src/hooks/useGame.ts`

```typescript
import { useContext } from 'react';
import { GameContext } from '../context/GameContext';

export const useGame = () => {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error('useGame must be used within GameProvider');
  }
  return context;
};
```

---

## 5. Layout Components

### `src/components/layout/Header.tsx`

```typescript
import React from 'react';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../ui/button';

export const Header: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-gray-900">🐀 No Rats</h1>
          {user && (
            <div className="text-sm text-gray-600">
              <p className="font-semibold">{user.name}</p>
              <p className="text-xs">Nível {user.level} • 🔥 {user.streak}</p>
            </div>
          )}
        </div>
        {user && (
          <Button
            variant="outline"
            size="sm"
            onClick={logout}
          >
            Sair
          </Button>
        )}
      </div>
    </header>
  );
};
```

### `src/components/layout/MainLayout.tsx`

```typescript
import React from 'react';
import { Header } from './Header';

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
};
```

---

## 6. Common Components

### `src/components/common/InfestationIndicator.tsx`

```typescript
import React from 'react';
import { cn } from '../../lib/utils';

interface InfestationIndicatorProps {
  value: number; // 0-100
  label?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const InfestationIndicator: React.FC<InfestationIndicatorProps> = ({
  value,
  label,
  size = 'md',
}) => {
  const percentage = Math.min(100, Math.max(0, value));
  
  // Color based on infestation level
  let bgColor = 'bg-green-500'; // 0-30
  let textColor = 'text-green-700';
  
  if (percentage > 60) {
    bgColor = 'bg-red-500'; // 61-100
    textColor = 'text-red-700';
  } else if (percentage > 30) {
    bgColor = 'bg-yellow-500'; // 31-60
    textColor = 'text-yellow-700';
  }

  const sizeClass = {
    sm: 'h-2',
    md: 'h-4',
    lg: 'h-6',
  }[size];

  const labelSize = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  }[size];

  return (
    <div className="space-y-2">
      {label && <p className={cn('font-medium', labelSize, textColor)}>{label}</p>}
      <div className="w-full bg-gray-200 rounded-full overflow-hidden">
        <div
          className={cn('transition-all duration-300 flex items-center justify-end pr-2', bgColor, sizeClass)}
          style={{ width: `${percentage}%` }}
        >
          {size !== 'sm' && <span className="text-white text-xs font-bold">{Math.round(percentage)}%</span>}
        </div>
      </div>
    </div>
  );
};
```

### `src/components/common/XPBar.tsx`

```typescript
import React from 'react';

interface XPBarProps {
  current: number;
  next: number;
  level: number;
}

export const XPBar: React.FC<XPBarProps> = ({ current, next, level }) => {
  const percentage = next > 0 ? (current / next) * 100 : 0;

  return (
    <div className="bg-white p-4 rounded-lg shadow space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-sm font-semibold text-gray-700">Nível {level}</span>
        <span className="text-xs text-gray-500">
          {current} / {next} XP
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full overflow-hidden h-3">
        <div
          className="bg-blue-500 transition-all duration-300 h-full"
          style={{ width: `${Math.min(100, percentage)}%` }}
        />
      </div>
    </div>
  );
};
```

---

## 7. Pages

### `src/pages/auth/Login.tsx`

```typescript
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await login(email, password);
      navigate('/onboarding');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Falha ao fazer login');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full space-y-6">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-2">🐀 No Rats</h1>
          <p className="text-gray-600">Gamifique suas tarefas domésticas</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 text-red-700 p-3 rounded text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              E-mail
            </label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="seu@email.com"
              disabled={loading}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Senha
            </label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              disabled={loading}
              required
            />
          </div>

          <Button
            type="submit"
            disabled={loading}
            className="w-full"
          >
            {loading ? 'Entrando...' : 'Entrar'}
          </Button>
        </form>

        <div className="text-center text-sm text-gray-600">
          Não tem conta?{' '}
          <Link to="/register" className="text-indigo-600 hover:underline font-semibold">
            Crie uma
          </Link>
        </div>
      </div>
    </div>
  );
};
```

### `src/pages/auth/Register.tsx`

```typescript
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';

export const Register: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('As senhas não coincidem');
      return;
    }

    setLoading(true);
    try {
      await register(email, name, password);
      navigate('/onboarding');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Falha ao registrar');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full space-y-6">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-2">🐀 No Rats</h1>
          <p className="text-gray-600">Crie sua conta</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 text-red-700 p-3 rounded text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nome
            </label>
            <Input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Seu nome"
              disabled={loading}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              E-mail
            </label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="seu@email.com"
              disabled={loading}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Senha
            </label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              disabled={loading}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirmar Senha
            </label>
            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              disabled={loading}
              required
            />
          </div>

          <Button
            type="submit"
            disabled={loading}
            className="w-full"
          >
            {loading ? 'Criando conta...' : 'Criar Conta'}
          </Button>
        </form>

        <div className="text-center text-sm text-gray-600">
          Já tem conta?{' '}
          <Link to="/login" className="text-indigo-600 hover:underline font-semibold">
            Faça login
          </Link>
        </div>
      </div>
    </div>
  );
};
```

### `src/pages/onboarding/Onboarding.tsx`

```typescript
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGame } from '../../hooks/useGame';
import { roomService } from '../../services/roomService';
import { Button } from '../../components/ui/button';
import { Checkbox } from '../../components/ui/checkbox';
import { ROOM_NAMES } from '../../types';

const AVAILABLE_ROOMS = Object.entries(ROOM_NAMES).map(([key, label]) => ({
  value: key,
  label,
  emoji: {
    cozinha: '🍳',
    banheiro: '🚿',
    quarto: '🛏️',
    sala: '🛋️',
    lavanderia: '🧺',
    escritorio: '🖥️',
  }[key],
}));

export const Onboarding: React.FC = () => {
  const navigate = useNavigate();
  const { refreshRooms } = useGame();
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const toggleRoom = (roomValue: string) => {
    setSelected((prev) =>
      prev.includes(roomValue)
        ? prev.filter((r) => r !== roomValue)
        : [...prev, roomValue]
    );
  };

  const handleSubmit = async () => {
    if (selected.length === 0) {
      setError('Selecione pelo menos um cômodo');
      return;
    }

    setLoading(true);
    try {
      await roomService.setupHouse(selected);
      await refreshRooms();
      navigate('/dashboard');
    } catch (err: any) {
      setError('Erro ao configurar cômodos');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-100 flex items-center justify-center px-4">
      <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full space-y-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold mb-2">Bem-vindo! 🏠</h1>
          <p className="text-gray-600">
            Qual é sua casa? Selecione os cômodos que você tem.
          </p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-700 p-3 rounded text-sm">
            {error}
          </div>
        )}

        <div className="space-y-3">
          {AVAILABLE_ROOMS.map((room) => (
            <label
              key={room.value}
              className="flex items-center gap-3 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-indigo-300 transition"
            >
              <Checkbox
                checked={selected.includes(room.value)}
                onCheckedChange={() => toggleRoom(room.value)}
              />
              <span className="text-2xl">{room.emoji}</span>
              <span className="text-gray-700 font-medium">{room.label}</span>
            </label>
          ))}
        </div>

        <Button
          onClick={handleSubmit}
          disabled={loading || selected.length === 0}
          className="w-full"
        >
          {loading ? 'Configurando...' : 'Começar'}
        </Button>
      </div>
    </div>
  );
};
```

### `src/pages/dashboard/Dashboard.tsx`

```typescript
import React, { useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { useGame } from '../../hooks/useGame';
import { useNavigate } from 'react-router-dom';
import { MainLayout } from '../../components/layout/MainLayout';
import { XPBar } from '../../components/common/XPBar';
import { InfestationIndicator } from '../../components/common/InfestationIndicator';
import { Button } from '../../components/ui/button';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const { rooms, tasks, loading, completeTask } = useGame();
  const navigate = useNavigate();

  if (!user) {
    navigate('/login');
    return null;
  }

  // Tarefas pendentes mais próximas de vencer
  const pendingTasks = tasks
    .filter((t) => t.status === 'pendente')
    .sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime())
    .slice(0, 5);

  const tasksByRoom = Object.fromEntries(
    rooms.map((room) => [
      room.id,
      tasks.filter((t) => t.room === room.id && t.status === 'pendente'),
    ])
  );

  return (
    <MainLayout>
      <div className="space-y-8">
        {/* Top Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="text-gray-600 text-sm">Total de XP</p>
            <p className="text-3xl font-bold text-blue-600">{user.total_xp}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="text-gray-600 text-sm">Nível</p>
            <p className="text-3xl font-bold text-purple-600">{user.level}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="text-gray-600 text-sm">Sequência 🔥</p>
            <p className="text-3xl font-bold text-orange-600">{user.streak}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="text-gray-600 text-sm">Infestação Total</p>
            <p className="text-3xl font-bold text-red-600">
              {Math.round(user.total_infestation)}%
            </p>
          </div>
        </div>

        {/* XP Progress */}
        <div className="bg-white p-6 rounded-lg shadow">
          <XPBar
            current={user.level_xp}
            next={user.xp_for_next_level}
            level={user.level}
          />
        </div>

        {/* Global Infestation */}
        <div className="bg-white p-6 rounded-lg shadow">
          <InfestationIndicator
            value={user.total_infestation}
            label="Infestação Global da Casa"
            size="lg"
          />
        </div>

        {/* Rooms with Infestation */}
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Cômodos</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {rooms.map((room) => (
              <div
                key={room.id}
                className="bg-white p-6 rounded-lg shadow cursor-pointer hover:shadow-lg transition"
                onClick={() => navigate(`/tasks?room=${room.id}`)}
              >
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-xl font-semibold text-gray-900">
                    {room.room_name}
                  </h3>
                  <span className="text-xs bg-gray-100 px-2 py-1 rounded">
                    {tasksByRoom[room.id]?.length || 0} tarefas
                  </span>
                </div>
                <InfestationIndicator
                  value={room.infestation}
                  label={`Infestação`}
                  size="md"
                />
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Ações Rápidas</h2>
          <div className="bg-white p-6 rounded-lg shadow space-y-3">
            {loading ? (
              <p className="text-gray-600">Carregando tarefas...</p>
            ) : pendingTasks.length > 0 ? (
              <div className="space-y-2">
                {pendingTasks.map((task) => (
                  <div
                    key={task.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded"
                  >
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{task.title}</p>
                      <p className="text-xs text-gray-500">
                        {task.room_name} • {task.difficulty_display}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => completeTask(task.id)}
                    >
                      +{task.xp_value} XP
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-600">Nenhuma tarefa pendente!</p>
            )}
          </div>
        </div>

        {/* Create Task Button */}
        <div className="flex gap-3">
          <Button
            size="lg"
            className="flex-1"
            onClick={() => navigate('/tasks/create')}
          >
            + Nova Tarefa
          </Button>
          <Button
            variant="outline"
            size="lg"
            className="flex-1"
            onClick={() => navigate('/tasks')}
          >
            Ver Todas as Tarefas
          </Button>
        </div>
      </div>
    </MainLayout>
  );
};
```

### `src/pages/tasks/CreateTask.tsx`

```typescript
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGame } from '../../hooks/useGame';
import { taskService } from '../../services/taskService';
import { MainLayout } from '../../components/layout/MainLayout';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Select } from '../../components/ui/select';
import { RadioGroup, RadioGroupItem } from '../../components/ui/radio-group';
import { CreateTaskInput } from '../../types';

const DIFFICULTIES = [
  { value: 'simples', label: 'Simples', xp: 10 },
  { value: 'media', label: 'Média', xp: 25 },
  { value: 'dificil', label: 'Difícil', xp: 50 },
  { value: 'pesada', label: 'Pesada', xp: 100 },
];

const FREQUENCIES = [
  { value: 'diaria', label: 'Diária' },
  { value: 'semanal', label: 'Semanal' },
  { value: 'quinzenal', label: 'Quinzenal' },
  { value: 'mensal', label: 'Mensal' },
];

export const CreateTask: React.FC = () => {
  const navigate = useNavigate();
  const { rooms, refreshTasks } = useGame();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState<CreateTaskInput>({
    room: '',
    title: '',
    difficulty: 'simples',
    frequency: 'semanal',
  });

  const selectedDifficulty = DIFFICULTIES.find((d) => d.value === form.difficulty);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!form.room || !form.title) {
      setError('Preencha os campos obrigatórios');
      return;
    }

    setLoading(true);
    try {
      await taskService.create(form);
      await refreshTasks();
      navigate('/dashboard');
    } catch (err: any) {
      setError('Erro ao criar tarefa');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <MainLayout>
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Criar Nova Tarefa</h1>

        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-8 space-y-6">
          {error && (
            <div className="bg-red-50 text-red-700 p-4 rounded">
              {error}
            </div>
          )}

          {/* Room */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Cômodo *
            </label>
            <Select
              value={form.room}
              onValueChange={(value) =>
                setForm({ ...form, room: value })
              }
            >
              <option value="">Selecione um cômodo</option>
              {rooms.map((room) => (
                <option key={room.id} value={room.id}>
                  {room.room_name}
                </option>
              ))}
            </Select>
          </div>

          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Título da Tarefa *
            </label>
            <Input
              type="text"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="ex: Lavar louça"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Descrição
            </label>
            <textarea
              value={form.description || ''}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
              placeholder="Detalhes adicionais"
              className="w-full p-2 border border-gray-300 rounded-lg"
              rows={3}
            />
          </div>

          {/* Difficulty */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Dificuldade
            </label>
            <RadioGroup
              value={form.difficulty}
              onValueChange={(value) =>
                setForm({ ...form, difficulty: value as any })
              }
            >
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {DIFFICULTIES.map((d) => (
                  <label
                    key={d.value}
                    className="flex items-center gap-2 p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-300 transition"
                  >
                    <RadioGroupItem value={d.value} />
                    <div>
                      <p className="font-medium text-gray-900">{d.label}</p>
                      <p className="text-xs text-gray-500">+{d.xp} XP</p>
                    </div>
                  </label>
                ))}
              </div>
            </RadioGroup>
          </div>

          {/* Frequency */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Frequência
            </label>
            <Select
              value={form.frequency}
              onValueChange={(value) =>
                setForm({ ...form, frequency: value as any })
              }
            >
              {FREQUENCIES.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </Select>
          </div>

          {/* Summary */}
          {selectedDifficulty && (
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-900">
                Ao completar, você ganhará <span className="font-bold">
                  +{selectedDifficulty.xp} XP
                </span>
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <Button
              type="submit"
              disabled={loading}
              className="flex-1"
            >
              {loading ? 'Criando...' : 'Criar Tarefa'}
            </Button>
            <Button
              type="button"
              variant="outline"
              className="flex-1"
              onClick={() => navigate(-1)}
            >
              Cancelar
            </Button>
          </div>
        </form>
      </div>
    </MainLayout>
  );
};
```

### `src/pages/tasks/TaskList.tsx`

```typescript
import React, { useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useGame } from '../../hooks/useGame';
import { MainLayout } from '../../components/layout/MainLayout';
import { Button } from '../../components/ui/button';
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';

export const TaskList: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { rooms, tasks, completeTask, loading } = useGame();

  const selectedRoomId = searchParams.get('room');
  const selectedRoom = rooms.find((r) => r.id === selectedRoomId);

  // Filter tasks
  const filteredTasks = useMemo(() => {
    let filtered = tasks;
    if (selectedRoomId) {
      filtered = filtered.filter((t) => t.room === selectedRoomId);
    }
    return filtered.sort(
      (a, b) =>
        new Date(a.due_date).getTime() - new Date(b.due_date).getTime()
    );
  }, [tasks, selectedRoomId]);

  // Group by status
  const pendingTasks = filteredTasks.filter((t) => t.status === 'pendente');
  const expiredTasks = filteredTasks.filter((t) => t.status === 'vencida');
  const completedTasks = filteredTasks.filter((t) => t.status === 'concluida');

  const TaskCard: React.FC<{ task: any; canComplete?: boolean }> = ({
    task,
    canComplete = false,
  }) => (
    <div
      className={`p-4 border-2 rounded-lg flex justify-between items-start gap-4 ${
        task.status === 'vencida'
          ? 'border-red-200 bg-red-50'
          : task.status === 'concluida'
          ? 'border-green-200 bg-green-50'
          : 'border-gray-200 bg-white'
      }`}
    >
      <div className="flex-1">
        <p className="font-semibold text-gray-900">{task.title}</p>
        {task.description && (
          <p className="text-sm text-gray-600 mt-1">{task.description}</p>
        )}
        <div className="flex gap-2 mt-2 flex-wrap">
          <span className="text-xs bg-gray-100 px-2 py-1 rounded">
            {task.room_name}
          </span>
          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
            {task.difficulty_display}
          </span>
          <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
            {task.frequency_display}
          </span>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          {task.status === 'concluida'
            ? `Concluída ${formatDistanceToNow(new Date(task.completed_at), {
                locale: ptBR,
                addSuffix: true,
              })}`
            : `Vence ${formatDistanceToNow(new Date(task.due_date), {
                locale: ptBR,
                addSuffix: true,
              })}`}
        </p>
      </div>
      {canComplete && (
        <Button
          onClick={() => completeTask(task.id)}
          className="whitespace-nowrap"
        >
          +{task.xp_value} XP
        </Button>
      )}
    </div>
  );

  return (
    <MainLayout>
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-900">
            Tarefas {selectedRoom && `- ${selectedRoom.room_name}`}
          </h1>
          <Button onClick={() => navigate('/tasks/create')}>
            + Nova Tarefa
          </Button>
        </div>

        {/* Pending Tasks */}
        {pendingTasks.length > 0 && (
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              Pendentes ({pendingTasks.length})
            </h2>
            <div className="space-y-3">
              {pendingTasks.map((task) => (
                <TaskCard key={task.id} task={task} canComplete={true} />
              ))}
            </div>
          </div>
        )}

        {/* Expired Tasks */}
        {expiredTasks.length > 0 && (
          <div>
            <h2 className="text-xl font-bold text-red-900 mb-4">
              Vencidas ({expiredTasks.length})
            </h2>
            <div className="space-y-3">
              {expiredTasks.map((task) => (
                <TaskCard key={task.id} task={task} canComplete={true} />
              ))}
            </div>
          </div>
        )}

        {/* Completed Tasks */}
        {completedTasks.length > 0 && (
          <div>
            <h2 className="text-xl font-bold text-green-900 mb-4">
              Concluídas ({completedTasks.length})
            </h2>
            <div className="space-y-3">
              {completedTasks.map((task) => (
                <TaskCard key={task.id} task={task} canComplete={false} />
              ))}
            </div>
          </div>
        )}

        {filteredTasks.length === 0 && !loading && (
          <div className="text-center py-12">
            <p className="text-gray-600 text-lg">Nenhuma tarefa encontrada</p>
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => navigate('/tasks/create')}
            >
              Criar primeira tarefa
            </Button>
          </div>
        )}
      </div>
    </MainLayout>
  );
};
```

---

## 8. Utility Functions

### `src/utils/storage.ts`

```typescript
import { AuthTokens } from '../types';

const STORAGE_KEY = 'no_rats_auth';

export const setStoredToken = (tokens: AuthTokens | null) => {
  if (tokens) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
};

export const getStoredToken = (): AuthTokens | null => {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored ? JSON.parse(stored) : null;
};

export const clearStoredToken = () => {
  localStorage.removeItem(STORAGE_KEY);
};
```

### `src/lib/utils.ts`

```typescript
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

---

## 9. App & Routing

### `src/App.tsx`

```typescript
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { GameProvider } from './context/GameContext';
import { useAuth } from './hooks/useAuth';

// Pages
import { Login } from './pages/auth/Login';
import { Register } from './pages/auth/Register';
import { Onboarding } from './pages/onboarding/Onboarding';
import { Dashboard } from './pages/dashboard/Dashboard';
import { TaskList } from './pages/tasks/TaskList';
import { CreateTask } from './pages/tasks/CreateTask';

// Protected route wrapper
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Carregando...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  return <>{children}</>;
};

function AppRoutes() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route
        path="/onboarding"
        element={
          <ProtectedRoute>
            <Onboarding />
          </ProtectedRoute>
        }
      />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <GameProvider user={user}>
              <Dashboard />
            </GameProvider>
          </ProtectedRoute>
        }
      />

      <Route
        path="/tasks"
        element={
          <ProtectedRoute>
            <GameProvider user={user}>
              <TaskList />
            </GameProvider>
          </ProtectedRoute>
        }
      />

      <Route
        path="/tasks/create"
        element={
          <ProtectedRoute>
            <GameProvider user={user}>
              <CreateTask />
            </GameProvider>
          </ProtectedRoute>
        }
      />

      <Route path="/" element={<Navigate to="/dashboard" />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
```

### `src/main.tsx`

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

### `src/index.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  * {
    @apply box-border;
  }
}
```

---

## 10. Configurações

### `vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify(
      process.env.VITE_API_URL || 'http://localhost:8000/api/v1'
    ),
  },
})
```

### `tailwind.config.ts`

```typescript
import type { Config } from 'tailwindcss'

export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
} satisfies Config
```

### `.env.local`

```
VITE_API_URL=http://localhost:8000/api/v1
```

---

## 11. Por que Context API?

**Decisão:** Context API + React Hooks (vs Redux/Zustand)

**Justificativa:**
- **MVP scope:** 2 contexts (Auth, Game); sem estado complexo
- **Simples:** Context está embutido; zero dependências adicionais
- **Suficiente:** Rerender em mudanças é OK para user count esperado
- **Prototipagem rápida:** Menos boilerplate que Redux
- **Futuro:** Se escalar, migrar para Zustand é trivial (mesmo API)

**Trade-off rejeitado:**
- Redux: Overkill para MVP; muita cerimônia
- Zustand: Ótimo, mas overkill; Context é mais direto
- Local storage tudo: Perde reatividade entre abas/componentes

---

## 12. Estrutura Final

```
Frontend:
  ✅ Auth (login, register) com JWT
  ✅ Onboarding (setup rooms)
  ✅ Dashboard (XP, nível, streak, infestação)
  ✅ Task CRUD (criar, listar, completar)
  ✅ Real-time sync com backend
  ✅ Context API para estado global
  ✅ TypeScript full
  ✅ Tailwind + shadcn/ui
  ✅ Responsive design
```

---

## 13. Próximos Passos

```bash
# Instalar e rodar
npm install
npm run dev

# Build para produção
npm run build

# Variáveis de ambiente
cp .env.example .env.local
# Editar VITE_API_URL para seu backend
```

---

**Status:** Pronto para desenvolvimento. Frontend completo do MVP, end-to-end.
