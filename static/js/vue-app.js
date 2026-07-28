/**
 * Skill Agent 管理平台 - Vue 3 应用
 */
const { createApp, ref, reactive, computed, onMounted, nextTick, watch } = Vue;

// ========================================
// 登录状态管理
// ========================================
const auth = {
    token: localStorage.getItem('auth_token') || null,
    user: JSON.parse(localStorage.getItem('auth_user') || 'null'),

    isLoggedIn() {
        return !!this.token;
    },

    setAuth(token, user) {
        this.token = token;
        this.user = user;
        localStorage.setItem('auth_token', token);
        localStorage.setItem('auth_user', JSON.stringify(user));
    },

    clearAuth() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
    },

    getAuthHeaders() {
        return this.token ? { 'Authorization': `Bearer ${this.token}` } : {};
    }
};

// ========================================
// API 工具
// ========================================
const api = {
    async request(url, options = {}) {
        const headers = {
            ...options.headers,
            ...auth.getAuthHeaders()
        };
        const res = await fetch(url, { ...options, headers });
        if (res.status === 401) {
            // 认证失败，清除登录状态
            auth.clearAuth();
            window.location.reload();
            return { code: 401, message: '登录已过期，请重新登录' };
        }
        if (res.status === 403) {
            // 权限不足，返回错误信息但不退出登录
            const data = await res.json();
            return { code: 403, success: false, message: data.detail || '权限不足' };
        }
        return res.json();
    },

    async get(url) {
        return this.request(url);
    },

    async post(url, data) {
        return this.request(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    },

    async put(url, data) {
        return this.request(url, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    },

    async del(url) {
        return this.request(url, { method: 'DELETE' });
    },

    async upload(url, formData) {
        return this.request(url, {
            method: 'POST',
            body: formData
        });
    }
};

function formatDate(dateStr) {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleString('zh-CN');
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// 解析 ECharts 图表标记并渲染
function renderECharts(content) {
    if (!content) return { html: '', charts: [] };
    try {
        const charts = [];
        const placeholders = [];
        let index = 0;
        
        // 调试：检查是否包含 ECharts 标记
        const hasECharts = content.includes('---ECHARTS_START---');
        if (hasECharts) {
            console.log('renderECharts: 检测到 ECharts 标记');
        }
        
        // 第一步：替换 ECharts 标记为安全的占位符
        const echartsRegex = /---ECHARTS_START---\s*([\s\S]*?)\s*---ECHARTS_END---/g;
        const textWithPlaceholders = content.replace(echartsRegex, (match, jsonStr) => {
            try {
                const chartData = JSON.parse(jsonStr.trim());
                const chartId = 'echart-' + Math.random().toString(36).substr(2, 9);
                const placeholder = `ECHARTS_PLACEHOLDER_${index}_PLACEHOLDER`;
                charts.push({ id: chartId, data: chartData });
                placeholders.push({ placeholder, chartId });
                index++;
                console.log('renderECharts: 解析图表成功', chartId, chartData.title || '无标题');
                return placeholder;
            } catch (e) {
                console.error('解析 ECharts 数据失败:', e);
                return match;
            }
        });
        
        if (charts.length > 0) {
            console.log('renderECharts: 共解析', charts.length, '个图表');
        }
        
        // 第二步：渲染 Markdown
        let html = marked.parse(textWithPlaceholders, { breaks: true });
        
        // 第三步：将占位符替换为真实的图表 div
        // 使用正则表达式，允许 marked 可能添加的 <p> 或其他标签
        placeholders.forEach(({ placeholder, chartId }) => {
            const placeholderRegex = new RegExp(
                '(?:<p>)?\\s*' + placeholder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s*(?:</p>)?',
                'g'
            );
            html = html.replace(
                placeholderRegex,
                `<div id="${chartId}" class="echarts-container" style="width:100%;height:300px;margin:16px 0;"></div>`
            );
        });
        
        // 第四步：清除任何残留的 <p> 标签对图表 div 的包裹
        // 循环处理直到没有匹配，应对嵌套情况
        let prevHtml;
        do {
            prevHtml = html;
            html = html.replace(
                /<p>\s*(<div\s+id="echart-[^"]*"\s+class="echarts-container"[^>]*><\/div>)\s*<\/p>/g,
                '$1'
            );
        } while (html !== prevHtml);
        
        return { html, charts };
    } catch (e) {
        console.error('renderECharts 整体处理失败:', e);
        // 回退：直接渲染纯 Markdown
        return { html: marked.parse(content, { breaks: true }), charts: [] };
    }
}

function renderMarkdown(text) {
    if (!text) return '';
    return marked.parse(text, { breaks: true });
}

// 初始化 ECharts 图表
function initECharts(charts) {
    console.log('initECharts: 开始初始化', charts.length, '个图表');
    if (!charts || charts.length === 0) return;
    if (typeof echarts === 'undefined') {
        console.warn('ECharts 库未加载');
        return;
    }
    
    charts.forEach(chart => {
        const dom = document.getElementById(chart.id);
        console.log('initECharts: 查找 DOM', chart.id, dom ? '找到' : '未找到');
        if (dom) {
            try {
                // 如果已经存在实例，先销毁避免冲突
                const existing = echarts.getInstanceByDom(dom);
                if (existing) existing.dispose();
                
                const instance = echarts.init(dom);
                // chart.data 直接是 ECharts option 配置
                if (chart.data) {
                    instance.setOption(chart.data);
                    console.log('initECharts: 图表渲染成功', chart.id, chart.data.title || '无标题');
                } else {
                    console.warn('initECharts: 图表数据为空', chart.id);
                }
                window.addEventListener('resize', () => instance.resize());
            } catch (e) {
                console.error('ECharts 渲染失败:', chart.id, e);
            }
        } else {
            console.warn('ECharts DOM 元素未找到:', chart.id,
                'DOM 可能尚未渲染，将在 300ms 后重试');
            // 延迟重试，应对复杂渲染场景（如图文混排）
            setTimeout(() => {
                const retryDom = document.getElementById(chart.id);
                console.log('initECharts: 重试查找 DOM', chart.id, retryDom ? '找到' : '未找到');
                if (retryDom) {
                    try {
                        const instance = echarts.init(retryDom);
                        // chart.data 直接是 ECharts option 配置
                        if (chart.data) {
                            instance.setOption(chart.data);
                            console.log('initECharts: 图表重试渲染成功', chart.id);
                        }
                        window.addEventListener('resize', () => instance.resize());
                    } catch (e) {
                        console.error('ECharts 重试渲染失败:', chart.id, e);
                    }
                }
            }, 300);
        }
    });
}

// ========================================
// Vue 应用
// ========================================
createApp({
    setup() {
        // ---- 登录状态 ----
        const isLoggedIn = ref(auth.isLoggedIn());
        const currentUser = ref(auth.user);
        const token = ref(auth.token);
        const loginForm = reactive({ username: '', password: '' });
        const loginLoading = ref(false);
        const loginError = ref('');

        // ---- 修改密码 ----
        const showChangePasswordModal = ref(false);
        const changePasswordForm = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' });
        const changePasswordLoading = ref(false);
        const changePasswordError = ref('');

        // ---- 用户菜单 ----
        const userMenuOpen = ref(false);
        const userMenus = ref([]);

        // ---- 全局状态 ----
        const currentPage = ref('agents');
        const toasts = ref([]);
        const sidebarOpen = ref(false);

        // ---- 数据 ----
        const agents = ref([]);
        const skills = ref([]);
        const executions = ref(JSON.parse(localStorage.getItem('executions') || '[]'));

        // ---- 仪表盘数据 ----
        const dashboardData = ref({
            agents: { total: 0, active: 0, today_count: 0 },
            skills: { total: 0, today_count: 0 },
            mcps: { total: 0, active: 0, today_count: 0 },
            users: { total: 0, active: 0, today_count: 0 },
            chats: { total: 0, today_count: 0, conversation_count: 0 },
            departments: { total: 0, active: 0 }
        });
        const dashboardActivities = ref([]);
        const dashboardLoading = ref(false);
        const pieChartRef = ref(null);
        const lineChartRef = ref(null);
        const popularData = ref({
            popular_agents: [],
            popular_skills: [],
            popular_mcps: []
        });
        const dailyStats = ref([]);
        const currentDate = ref(new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }));
        const systemUptime = ref('0天 0小时');

        // ---- 分页状态 ----
        const agentPage = ref(1);
        const agentPageSize = ref(10);
        const agentTotal = ref(0);
        const agentTotalPages = ref(1);
        const skillPage = ref(1);
        const skillPageSize = ref(10);
        const skillTotal = ref(0);
        const skillTotalPages = ref(1);

        // ---- Agent 页面 ----
        const selectedAgent = ref(null);
        const agentSearch = ref('');
        const showCreateAgentModal = ref(false);
        const isEditingAgent = ref(false);
        const showSettingsPanel = ref(false);
        const agentForm = reactive({ id: null, name: '', description: '', skills: [], tools: [], modelId: '', promptId: '', agentSpace: 'private', isLocked: false, createdBy: null, options: { enableMemory: false, enableSearch: false, enableCodeExec: false, language: 'auto', maxTokens: '1024' } });
        const availableTools = ref([]);
        const availableModels = ref([]);
        const availablePrompts = ref([]);
        const createToolDropdown = ref(false);
        const createToolSearch = ref('');
        const createPromptDropdown = ref(false);
        const createPromptSearch = ref('');
        const settingsForm = reactive({ name: '', description: '', skillIds: [], skillNames: {}, toolIds: [], toolNames: {}, modelId: '', promptId: '', promptName: '', configParams: [], temperature: 0.7, topP: 0.9, enableMemory: true, agentSpace: 'private', isLocked: false });
        const settingsSkillDropdown = ref(false);
        const settingsSkillSearch = ref('');
        const settingsToolDropdown = ref(false);
        const settingsToolSearch = ref('');
        const settingsPromptDropdown = ref(false);
        const settingsPromptSearch = ref('');
        const createSkillDropdown = ref(false);
        const createSkillSearch = ref('');

        // ---- Skill 页面 ----
        const skillSearch = ref('');
        const showCreateSkillModal = ref(false);
        const showEditSkillModal = ref(false);
        const creatingSkill = ref(false);
        const skillForm = reactive({ name: '', description: '', code: '', skillSpace: 'private' });
        const editSkillForm = reactive({ id: '', name: '', description: '', code: '', skillSpace: 'private' });

        // ---- 提示词管理页面 ----
        const prompts = ref([]);
        const promptPage = ref(1);
        const promptPageSize = ref(10);
        const promptTotal = ref(0);
        const promptTotalPages = ref(1);
        const promptSearch = ref('');
        const showCreatePromptModal = ref(false);
        const isEditingPrompt = ref(false);
        const creatingPrompt = ref(false);
        const promptForm = reactive({
            id: '', name: '', content: '', description: '',
            type: 'private', is_active: true
        });

        // ---- 聊天 ----
        const chatMessages = ref([]);
        const chatInput = ref('');
        const chatLoading = ref(false);
        const currentConversationId = ref('');
        const uploadedFiles = ref([]); // 已上传文件列表
        const isUploading = ref(false); // 上传中状态
        let chatAbortController = null; // 用于终止对话的 AbortController

        // Conversation ID 本地存储管理
        const CONVERSATION_STORAGE_KEY = 'skillagent_conversations';

        function getStoredConversationId(agentId) {
            try {
                const stored = localStorage.getItem(CONVERSATION_STORAGE_KEY);
                if (stored) {
                    const conversations = JSON.parse(stored);
                    return conversations[agentId] || null;
                }
            } catch (e) {
                console.error('读取 conversation_id 失败:', e);
            }
            return null;
        }

        function setStoredConversationId(agentId, conversationId) {
            try {
                let conversations = {};
                const stored = localStorage.getItem(CONVERSATION_STORAGE_KEY);
                if (stored) {
                    conversations = JSON.parse(stored);
                }
                conversations[agentId] = conversationId;
                localStorage.setItem(CONVERSATION_STORAGE_KEY, JSON.stringify(conversations));
            } catch (e) {
                console.error('保存 conversation_id 失败:', e);
            }
        }

        function generateConversationId() {
            return 'conv_' + crypto.randomUUID().replace(/-/g, '');
        }

        // ---- 执行记录 ----
        const showExecutionResultModal = ref(false);
        const currentExecution = ref(null);

        // ---- 权限 tab ----
        const permissionTab = ref('users');

        // ---- MCP管理 ----
        const mcpServers = ref([]);
        const mcpPage = ref(1);
        const mcpPageSize = ref(10);
        const mcpTotal = ref(0);
        const mcpTotalPages = ref(0);
        const showMcpModal = ref(false);
        const isEditingMcp = ref(false);
        const syncingMcpId = ref(null);
        const selectedMcpId = ref(null);
        const mcpTools = ref([]);
        const showToolDebugModal = ref(false);
        const debugTool = reactive({ name: '', description: '', parameters: {} });
        const debugToolResult = ref(null);
        const invokingTool = ref(false);
        const mcpForm = reactive({ id: null, name: '', type: 'sse', endpoint: '', visibility: 'private', description: '' });

        // ---- 模型管理 ----
        const models = ref([]);
        const modelPage = ref(1);
        const modelPageSize = ref(10);
        const modelTotal = ref(0);
        const modelTotalPages = ref(0);
        const showModelModal = ref(false);
        const isEditingModel = ref(false);
        const testingModelId = ref(null);
        const modelForm = reactive({
            id: null,
            name: '',
            modelType: 'chat',
            provider: 'openai',
            modelName: '',
            baseUrl: '',
            apiKey: '',
            description: ''
        });

        // ---- 权限管控 - 用户管理 ----
        const permissionUsers = ref([]);
        const showUserModal = ref(false);
        const isEditingUser = ref(false);
        const userForm = reactive({
            id: null,
            username: '',
            email: '',
            real_name: '',
            phone: '',
            department_id: '',
            role_ids: [],
            status: 'active',
            password: ''
        });

        // ---- 权限管控 - 部门管理 ----
        const departments = ref([]);
        const departmentTree = ref([]);
        const showDepartmentModal = ref(false);
        const isEditingDepartment = ref(false);
        const departmentForm = reactive({
            id: null,
            name: '',
            code: '',
            parent_id: '',
            description: '',
            sort_order: 0,
            status: 'active'
        });

        // ---- 权限管控 - 角色管理 ----
        const permissionRoles = ref([]);
        const showRoleModal = ref(false);
        const isEditingRole = ref(false);
        const roleForm = reactive({
            id: null,
            name: '',
            code: '',
            description: '',
            permission_ids: [],
            status: 'active'
        });

        // ---- 权限管控 - 权限管理 ----
        const allPermissions = ref([]);
        const showPermissionModal = ref(false);
        const isEditingPermission = ref(false);
        const permissionForm = reactive({
            id: null,
            key: '',
            name: '',
            is_menu: false,
            menu_path: '',
            menu_icon: '',
            menu_order: 0,
            status: true
        });

        // ---- 知识库管理 ----
        const knowledgeBases = ref([]);
        const kbPage = ref(1);
        const kbPageSize = ref(10);
        const kbTotal = ref(0);
        const kbTotalPages = ref(0);
        const kbSearch = ref('');
        const showKbModal = ref(false);
        const isEditingKb = ref(false);
        const kbForm = reactive({
            id: null,
            name: '',
            description: '',
            embedding_model: '',
            type: 'private'
        });
        const kbDocuments = ref([]);
        const showKbDocModal = ref(false);
        const kbDocForm = reactive({
            title: '',
            content: '',
            kb_id: ''
        });

        // 知识库详情弹窗
        const showKbDetailModal = ref(false);
        const currentKb = ref(null);
        const kbDetailTab = ref('upload'); // upload, test
        const kbUploadFiles = ref([]);
        const kbTestQuery = ref('');
        const kbTestResults = ref([]);
        const kbTestLoading = ref(false);

        // ========================================
        // 计算属性
        // ========================================
        const pageTitles = {
            dashboard: '仪表盘', agents: 'Agent管理', skills: 'Skill管理',
            mcp: 'MCP管理', models: '模型管理', permission: '权限管控',
            rag: '知识库管理'
        };
        const pageTitle = computed(() => pageTitles[currentPage.value] || 'Skill Agent');

        // 根据菜单权限生成页面标题映射
        const dynamicPageTitles = computed(() => {
            const titles = {};
            userMenus.value.forEach(menu => {
                if (menu.path) {
                    titles[menu.path] = menu.name;
                }
            });
            return { ...pageTitles, ...titles };
        });

        const filteredAgents = computed(() => {
            const q = agentSearch.value.toLowerCase();
            if (!q) return agents.value;
            return agents.value.filter(a =>
                a.name.toLowerCase().includes(q) || (a.description || '').toLowerCase().includes(q)
            );
        });

        const filteredSkills = computed(() => {
            const q = skillSearch.value.toLowerCase();
            if (!q) return skills.value;
            return skills.value.filter(s =>
                s.name.toLowerCase().includes(q) || (s.description || '').toLowerCase().includes(q)
            );
        });

        const filteredSettingsSkills = computed(() => {
            const q = settingsSkillSearch.value.toLowerCase();
            // 合并当前用户可见的技能和已绑定的技能
            const boundSkills = settingsForm.skillIds
                .filter(id => !skills.value.find(s => s.id === id))
                .map(id => ({ id, name: settingsForm.skillNames[id] || id }));
            const allSkills = [...skills.value, ...boundSkills];
            if (!q) return allSkills;
            return allSkills.filter(s => s.name.toLowerCase().includes(q));
        });

        const filteredSettingsTools = computed(() => {
            const q = settingsToolSearch.value.toLowerCase();
            // 合并当前用户可见的工具和已绑定的工具
            const boundTools = settingsForm.toolIds
                .filter(id => !availableTools.value.find(t => t.id === id))
                .map(id => ({ id, name: settingsForm.toolNames[id] || id }));
            const allTools = [...availableTools.value, ...boundTools];
            if (!q) return allTools;
            return allTools.filter(t => t.name.toLowerCase().includes(q));
        });

        const filteredSettingsPrompts = computed(() => {
            const q = settingsPromptSearch.value.toLowerCase();
            if (!q) return availablePrompts.value;
            return availablePrompts.value.filter(p =>
                p.name.toLowerCase().includes(q) || (p.description || '').toLowerCase().includes(q)
            );
        });

        const filteredCreatePrompts = computed(() => {
            const q = createPromptSearch.value.toLowerCase();
            if (!q) return availablePrompts.value;
            return availablePrompts.value.filter(p =>
                p.name.toLowerCase().includes(q) || (p.description || '').toLowerCase().includes(q)
            );
        });

        const filteredCreateSkills = computed(() => {
            const q = createSkillSearch.value.toLowerCase();
            if (!q) return skills.value;
            return skills.value.filter(s => s.name.toLowerCase().includes(q));
        });

        const dashboardStats = computed(() => {
            const total = executions.value.length;
            const success = executions.value.filter(e => e.status === 'success').length;
            return {
                agentCount: agents.value.length,
                skillCount: skills.value.length,
                executionCount: total,
                successRate: total > 0 ? Math.round((success / total) * 100) + '%' : '0%'
            };
        });

        // 渲染聊天消息（支持 ECharts 图表）
        const renderedChatMessages = computed(() => {
            return chatMessages.value.map(msg => {
                if (msg.role === 'user') {
                    return msg;
                }
                // 解析 ECharts 标记（内部已处理 Markdown 渲染）
                const { html, charts } = renderECharts(msg.content);
                return {
                    ...msg,
                    renderedContent: html,
                    _charts: charts // 保存图表数据供 watch 使用
                };
            });
        });

        // 监听消息变化，渲染 ECharts 图表
        watch(renderedChatMessages, async (newMessages) => {
            console.log('watch: renderedChatMessages 变化，消息数:', newMessages.length);
            // 收集所有需要渲染的图表
            const allCharts = [];
            newMessages.forEach((msg, idx) => {
                if (msg._charts && msg._charts.length > 0) {
                    console.log('watch: 消息', idx, '包含', msg._charts.length, '个图表');
                    allCharts.push(...msg._charts);
                }
            });
            // 等待 DOM 渲染完成后初始化图表
            if (allCharts.length > 0) {
                console.log('watch: 准备渲染', allCharts.length, '个图表');
                await nextTick();
                console.log('watch: DOM 已更新，开始初始化图表');
                initECharts(allCharts);
            }
        }, { deep: true });

        // ========================================
        // Toast
        // ========================================
        function showToast(message, type = 'info', duration = 3000) {
            const id = Date.now() + Math.random();
            toasts.value.push({ id, message, type });
            setTimeout(() => {
                toasts.value = toasts.value.filter(t => t.id !== id);
            }, duration);
        }

        // ========================================
        // 导航
        // ========================================
        function switchPage(page) {
            currentPage.value = page;
            sidebarOpen.value = false;
            if (page === 'dashboard') {
                loadDashboard();
                // 切换回 dashboard 时重新初始化图表 - 增加延迟确保 DOM 完全准备好
                setTimeout(() => {
                    nextTick(() => {
                        initCharts();
                    });
                }, 300);
            }
            else if (page === 'agents') loadAgents();
            else if (page === 'skills') loadSkills();
            else if (page === 'models') loadModels();
            else if (page === 'mcp') loadMcps();
            else if (page === 'prompts') loadPrompts();
            else if (page === 'rag') loadKnowledgeBases();
            else if (page === 'permission') {
                loadPermissionUsers();
                loadPermissionRoles();
                loadAllPermissions();
                loadDepartments();
            }
        }

        // ========================================
        // Agent 管理
        // ========================================
        async function loadAgents() {
            try {
                // 如果有搜索关键词，传递到后端进行数据库搜索
                const keyword = agentSearch.value?.trim();
                let url = `/api/agents/list?page=${agentPage.value}&page_size=${agentPageSize.value}`;
                if (keyword) {
                    url += `&keyword=${encodeURIComponent(keyword)}`;
                }
                const data = await api.get(url);
                if (data.success && data.data) {
                    agents.value = data.data.items || [];
                    agentTotal.value = data.data.total || 0;
                    agentTotalPages.value = data.data.total_pages || 1;
                    // 如果当前选中的agent在列表中，更新其数据
                    if (selectedAgent.value) {
                        const updatedAgent = agents.value.find(a => a.id === selectedAgent.value.id);
                        if (updatedAgent) {
                            selectedAgent.value = updatedAgent;
                        } else {
                            // 当前选中的agent对新用户不可见，清空选择
                            selectedAgent.value = null;
                            showSettingsPanel.value = false;
                        }
                    }
                }
            } catch (e) { console.error(e); }
        }

        async function selectAgent(agent) {
            selectedAgent.value = agent;
            showSettingsPanel.value = false;

            // 获取或生成 conversation_id
            let conversationId = getStoredConversationId(agent.id);
            if (!conversationId) {
                conversationId = generateConversationId();
                setStoredConversationId(agent.id, conversationId);
            }
            currentConversationId.value = conversationId;

            // 加载历史对话记录（使用conversation_id过滤）
            chatMessages.value = [];
            try {
                const historyData = await api.get(`/api/chat/history?agent_id=${agent.id}&conversation_id=${conversationId}`);
                if (historyData.success && historyData.data && historyData.data.length > 0) {
                    // 有历史记录，使用历史记录
                    chatMessages.value = historyData.data;
                } else {
                    // 无历史记录，显示欢迎消息
                    chatMessages.value = [{
                        role: 'agent',
                        content: `你好！我是${agent.name}，${agent.description || '你的智能助手'}。有什么可以帮你的吗？`,
                        time: new Date().toLocaleTimeString()
                    }];
                }
            } catch (e) {
                // 加载失败，显示欢迎消息
                chatMessages.value = [{
                    role: 'agent',
                    content: `你好！我是${agent.name}，${agent.description || '你的智能助手'}。有什么可以帮你的吗？`,
                    time: new Date().toLocaleTimeString()
                }];
            }
        }

        async function openCreateAgentModal() {
            console.log('openCreateAgentModal called - opening modal');
            isEditingAgent.value = false;
            agentForm.id = null;
            agentForm.name = '';
            agentForm.description = '';
            agentForm.skills = [];
            agentForm.tools = [];
            agentForm.modelId = '';
            agentForm.promptId = '';
            agentForm.agentSpace = 'private';
            agentForm.isLocked = false;
            agentForm.createdBy = null;
            Object.assign(agentForm.options, { enableMemory: false, enableSearch: false, enableCodeExec: false, language: 'auto', maxTokens: '1024' });
            // 确保技能列表已加载
            if (skills.value.length === 0) {
                await loadSkills();
            }
            // 加载工具、模型和提示词列表（只加载启用的提示词）
            await loadAvailableTools();
            await loadAvailableModels();
            await loadAvailablePrompts(true);
            // 立即显示弹窗
            showCreateAgentModal.value = true;
            window.modalOpenTime = Date.now();
            console.log('Modal opened at:', window.modalOpenTime);
            // 延迟绑定点击事件，避免当前点击穿透
            await nextTick();
            setTimeout(() => {
                const overlay = document.getElementById('agent-modal-overlay');
                const content = document.getElementById('agent-modal-content');
                if (overlay && content) {
                    const overlayRect = overlay.getBoundingClientRect();
                    const contentRect = content.getBoundingClientRect();
                    console.log('Overlay rect:', overlayRect);
                    console.log('Content rect:', contentRect);
                    console.log('User click was at (430, 290) - should be in content area if properly positioned');
                }
                if (overlay) {
                    overlay.addEventListener('click', handleOverlayClick);
                    console.log('Overlay click handler bound');
                }
            }, 200);
        }

        async function loadAvailableTools() {
            try {
                const data = await api.get('/api/mcps/tools/all');
                if (data.code === 200) {
                    availableTools.value = data.data.tools || [];
                }
            } catch (e) {
                console.error('加载工具列表失败:', e);
            }
        }

        async function loadAvailableModels() {
            try {
                const data = await api.get('/api/models/active');
                if (data.code === 200) {
                    availableModels.value = data.data.models || [];
                }
            } catch (e) {
                console.error('加载模型列表失败:', e);
            }
        }

        async function loadAvailablePrompts(onlyActive = false) {
            try {
                let url = '/api/prompts?page=1&page_size=100';
                if (onlyActive) {
                    url += '&is_active=true';
                }
                const data = await api.get(url);
                if (data.success) {
                    availablePrompts.value = data.data.items || [];
                }
            } catch (e) {
                console.error('加载提示词列表失败:', e);
            }
        }

        function toggleAgentTool(toolId) {
            const idx = agentForm.tools.indexOf(toolId);
            if (idx > -1) agentForm.tools.splice(idx, 1);
            else agentForm.tools.push(toolId);
        }

        const filteredCreateTools = computed(() => {
            if (!createToolSearch.value) return availableTools.value;
            const keyword = createToolSearch.value.toLowerCase();
            return availableTools.value.filter(t =>
                (t.name && t.name.toLowerCase().includes(keyword)) ||
                (t.description && t.description.toLowerCase().includes(keyword))
            );
        });

        function handleOverlayClick(event) {
            console.log('Overlay clicked');
            console.log('Click coordinates:', event.clientX, event.clientY);
            console.log('Time since open:', Date.now() - window.modalOpenTime);
            // 如果点击发生在弹窗打开后 300ms 内，忽略这次点击（可能是穿透点击）
            if (Date.now() - window.modalOpenTime < 300) {
                console.log('Ignoring click - too soon after open');
                return;
            }
            closeCreateAgentModal(event);
            // 移除事件监听器
            event.target.removeEventListener('click', handleOverlayClick);
        }

        function closeCreateAgentModal(event) {
            console.log('closeCreateAgentModal called - closing modal');
            console.log('Event target:', event ? event.target : 'no event');
            console.log('Event currentTarget:', event ? event.currentTarget : 'no event');
            console.trace('Stack trace for closeCreateAgentModal');
            showCreateAgentModal.value = false;
        }

        async function openEditAgentModal(agentId) {
            try {
                // 确保技能列表已加载
                if (skills.value.length === 0) {
                    await loadSkills();
                }
                // 加载工具、模型和提示词列表（只加载启用的提示词）
                await loadAvailableTools();
                await loadAvailableModels();
                await loadAvailablePrompts(true);
                const data = await api.get(`/api/agents/${agentId}`);
                if (data.success) {
                    const a = data.data;
                    isEditingAgent.value = true;
                    agentForm.id = a.id;
                    agentForm.name = a.name;
                    agentForm.description = a.description || '';
                    agentForm.skills = [...(a.skills || [])];
                    agentForm.tools = [...(a.tools || [])];
                    agentForm.modelId = a.model_id || '';
                    agentForm.promptId = a.prompt_id || '';
                    agentForm.agentSpace = a.agent_space || 'private';
                    agentForm.isLocked = a.is_locked || false;
                    agentForm.createdBy = a.created_by || null;
                    const opts = a.options || {};
                    Object.assign(agentForm.options, { enableMemory: !!opts.enableMemory, enableSearch: !!opts.enableSearch, enableCodeExec: !!opts.enableCodeExec, language: opts.language || 'auto', maxTokens: opts.maxTokens || '1024' });
                    showCreateAgentModal.value = true;
                }
            } catch (e) { showToast('加载失败', 'error'); }
        }

        async function saveAgent() {
            if (!agentForm.name.trim()) { showToast('请输入智能体名称', 'error'); return; }
            const payload = { name: agentForm.name, description: agentForm.description, skills: agentForm.skills, tools: agentForm.tools, model_id: agentForm.modelId, prompt_id: agentForm.promptId, agent_space: agentForm.agentSpace, is_locked: agentForm.isLocked, options: { ...agentForm.options } };
            try {
                const data = isEditingAgent.value
                    ? await api.put(`/api/agents/${agentForm.id}`, payload)
                    : await api.post('/api/agents/create', payload);
                if (data.success) {
                    showCreateAgentModal.value = false;
                    showToast(isEditingAgent.value ? '更新成功' : '创建成功', 'success');
                    loadAgents();
                } else { showToast(data.message || '操作失败', 'error'); }
            } catch (e) { showToast('网络错误', 'error'); }
        }

        async function openSettings(agent) {
            settingsForm.name = agent.name;
            settingsForm.description = agent.description || '';
            settingsForm.skillIds = [...(agent.skills || [])];
            settingsForm.skillNames = agent.skill_names || {};
            settingsForm.toolIds = [...(agent.tools || [])];
            settingsForm.toolNames = agent.tool_names || {};
            settingsForm.modelId = agent.model_id || '';
            settingsForm.promptId = agent.prompt_id || '';
            settingsForm.promptName = agent.prompt_name || (agent.prompt?.name || '');
            settingsForm.configParams = Object.entries(agent.config || {}).map(([key, value]) => ({ key, value }));
            // 加载模型参数（独立列），使用默认值
            settingsForm.temperature = agent.temperature ?? 0.7;
            settingsForm.topP = agent.top_p ?? 0.9;
            settingsForm.enableMemory = agent.enable_memory ?? true;
            settingsForm.isLocked = agent.is_locked ?? false;
            // 加载可见范围
            settingsForm.agentSpace = agent.agent_space || 'private';
            // 加载所有可用工具列表（用于下拉框选择）
            if (availableTools.value.length === 0) {
                await loadAvailableTools();
            }
            // 加载可用模型列表
            if (availableModels.value.length === 0) {
                await loadAvailableModels();
            }
            // 加载可用提示词列表（只加载启用的提示词）
            if (availablePrompts.value.length === 0) {
                await loadAvailablePrompts(true);
            }
            showSettingsPanel.value = true;
        }

        function startNewConversation() {
            if (!selectedAgent.value) return;
            // 生成新的 conversation_id
            const newConversationId = generateConversationId();
            currentConversationId.value = newConversationId;
            setStoredConversationId(selectedAgent.value.id, newConversationId);
            // 清空聊天记录，显示欢迎消息
            chatMessages.value = [{
                role: 'agent',
                content: `你好！我是${selectedAgent.value.name}，${selectedAgent.value.description || '你的智能助手'}。有什么可以帮你的吗？`,
                time: new Date().toLocaleTimeString()
            }];
            showToast('已开启新会话', 'success');
        }

        async function saveSettings() {
            if (!selectedAgent.value) return;
            const config = {};
            settingsForm.configParams.forEach(p => { if (p.key) config[p.key] = p.value; });
            // 模型参数作为独立字段传递
            const payload = {
                name: settingsForm.name,
                description: settingsForm.description,
                skills: settingsForm.skillIds,
                tools: settingsForm.toolIds,
                model_id: settingsForm.modelId,
                prompt_id: settingsForm.promptId,
                config,
                temperature: parseFloat(settingsForm.temperature),
                top_p: parseFloat(settingsForm.topP),
                enable_memory: Boolean(settingsForm.enableMemory),
                is_locked: Boolean(settingsForm.isLocked),
                agent_space: settingsForm.agentSpace
            };
            try {
                const data = await api.put(`/api/agents/${selectedAgent.value.id}`, payload);
                if (data.success) {
                    showSettingsPanel.value = false;
                    showToast('设置保存成功', 'success');
                    loadAgents();
                } else { showToast(data.message || '保存失败', 'error'); }
            } catch (e) { showToast('网络错误', 'error'); }
        }

        async function deleteAgent(agentId) {
            if (!confirm('确定要删除这个智能体吗？')) return;
            try {
                const data = await api.del(`/api/agents/${agentId}`);
                if (data.success) {
                    showToast('已删除', 'success');
                    selectedAgent.value = null;
                    showSettingsPanel.value = false;
                    loadAgents();
                } else {
                    showToast(data.message || data.detail || '删除失败', 'error');
                }
            } catch (e) { 
                showToast(e.message || '删除失败', 'error'); 
            }
        }

        async function downloadFile(url, filename) {
            try {
                const res = await fetch(url, {
                    headers: auth.getAuthHeaders()
                });
                if (!res.ok) {
                    if (res.status === 401 || res.status === 403) {
                        auth.clearAuth();
                        window.location.reload();
                        return;
                    }
                    throw new Error('下载失败');
                }
                const blob = await res.blob();
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(a.href);
            } catch (e) {
                throw e;
            }
        }

        async function exportAgent(agent) {
            try {
                await downloadFile(`/api/agents/${agent.id}/export`, `agent_${agent.name}.json`);
                showToast('Agent导出已开始', 'success');
            } catch (e) { showToast('导出失败', 'error'); }
        }

        async function importAgent() {
            const input = document.createElement('input');
            input.type = 'file'; input.accept = '.json';
            input.onchange = async e => {
                const file = e.target.files[0];
                if (!file) return;
                const formData = new FormData();
                formData.append('file', file);
                try {
                    const data = await api.upload('/api/agents/import', formData);
                    if (data.success) {
                        showToast(data.message || '导入成功', 'success');
                        loadAgents();
                    } else {
                        const errMsg = data.data && data.data.errors ? data.data.errors.join('; ') : (data.message || '导入失败');
                        showToast(errMsg, 'error');
                    }
                } catch (err) { showToast('导入网络错误', 'error'); }
            };
            input.click();
        }

        function toggleAgentSkill(skillId) {
            const idx = agentForm.skills.indexOf(skillId);
            if (idx > -1) agentForm.skills.splice(idx, 1);
            else agentForm.skills.push(skillId);
        }

        function toggleSettingsSkill(skillId) {
            const idx = settingsForm.skillIds.indexOf(skillId);
            if (idx > -1) settingsForm.skillIds.splice(idx, 1);
            else settingsForm.skillIds.push(skillId);
        }

        function toggleSettingsTool(toolId) {
            const idx = settingsForm.toolIds.indexOf(toolId);
            if (idx > -1) settingsForm.toolIds.splice(idx, 1);
            else settingsForm.toolIds.push(toolId);
        }

        function selectSettingsPrompt(prompt) {
            settingsForm.promptId = prompt.id;
            settingsForm.promptName = prompt.name;
            settingsPromptDropdown.value = false;
        }

        function selectCreatePrompt(prompt) {
            agentForm.promptId = prompt.id;
            createPromptDropdown.value = false;
        }

        function clearSettingsPrompt() {
            settingsForm.promptId = '';
            settingsForm.promptName = '';
        }

        function clearCreatePrompt() {
            agentForm.promptId = '';
        }

        // ========================================
        // Skill 管理
        // ========================================
        async function loadSkills() {
            try {
                // 如果有搜索关键词，传递到后端进行数据库搜索
                const keyword = skillSearch.value?.trim();
                let url = `/api/skills/list?page=${skillPage.value}&page_size=${skillPageSize.value}`;
                if (keyword) {
                    url += `&keyword=${encodeURIComponent(keyword)}`;
                }
                const data = await api.get(url);
                if (data.success && data.data) {
                    skills.value = data.data.items || [];
                    skillTotal.value = data.data.total || 0;
                    skillTotalPages.value = data.data.total_pages || 1;
                }
            } catch (e) { console.error(e); }
        }

        function openCreateSkillModal() {
            skillForm.name = ''; skillForm.description = ''; skillForm.code = ''; skillForm.skillSpace = 'private';
            showCreateSkillModal.value = true;
        }

        async function saveSkill() {
            if (!skillForm.name.trim()) { showToast('请输入Skill名称', 'error'); return; }
            creatingSkill.value = true;
            await nextTick();
            try {
                const data = await api.post('/api/skills/create', { name: skillForm.name, description: skillForm.description, code: skillForm.code, skill_space: skillForm.skillSpace });
                if (data.success) {
                    showCreateSkillModal.value = false;
                    showToast('Skill创建成功', 'success');
                    loadSkills();
                } else { showToast(data.message || '创建失败', 'error'); }
            } catch (e) { showToast('网络错误', 'error'); }
            finally { creatingSkill.value = false; }
        }

        async function openEditSkillModal(skillId) {
            try {
                const data = await api.get(`/api/skills/${skillId}`);
                if (data.success) {
                    const s = data.data;
                    editSkillForm.id = s.id;
                    editSkillForm.name = s.name;
                    editSkillForm.description = s.description || '';
                    editSkillForm.code = s.code || '';
                    editSkillForm.skillSpace = s.skill_space || 'private';
                    showEditSkillModal.value = true;
                } else { showToast(data.message || '获取失败', 'error'); }
            } catch (e) { showToast('网络错误', 'error'); }
        }

        async function saveEditSkill() {
            if (!editSkillForm.name.trim()) { showToast('请输入Skill名称', 'error'); return; }
            try {
                const data = await api.put(`/api/skills/${editSkillForm.id}`, {
                    name: editSkillForm.name, description: editSkillForm.description, code: editSkillForm.code, type: editSkillForm.skillSpace
                });
                if (data.success) {
                    showEditSkillModal.value = false;
                    showToast('Skill更新成功', 'success');
                    loadSkills();
                } else { showToast(data.message || '更新失败', 'error'); }
            } catch (e) { showToast('网络错误', 'error'); }
        }

        async function deleteSkill(skillId) {
            if (!confirm('确定要删除这个Skill吗？')) return;
            try {
                const data = await api.del(`/api/skills/${skillId}`);
                if (data.success) {
                    showToast('Skill已删除', 'success');
                    loadSkills();
                } else if (data.detail) {
                    showToast(data.detail, 'error');
                } else { showToast(data.message || '删除失败', 'error'); }
            } catch (e) { showToast('网络错误', 'error'); }
        }

        async function exportSkill(skill) {
            try {
                await downloadFile(`/api/skills/${skill.id}/export`, `skill_${skill.name}.zip`);
                showToast('Skill导出已开始', 'success');
            } catch (e) { showToast('导出失败', 'error'); }
        }

        async function importSkills() {
            const input = document.createElement('input');
            input.type = 'file'; input.accept = '.zip';
            input.onchange = async e => {
                const file = e.target.files[0];
                if (!file) return;
                const formData = new FormData();
                formData.append('file', file);
                try {
                    const data = await api.upload('/api/skills/import', formData);
                    if (data.success) {
                        showToast(data.message || '导入成功', 'success');
                        loadSkills();
                    } else { showToast(data.message || '导入失败', 'error'); }
                } catch (err) { showToast('导入网络错误', 'error'); }
            };
            input.click();
        }

        // ========================================
        // 分页导航
        // ========================================
        function changeAgentPage(p) {
            if (p < 1 || p > agentTotalPages.value) return;
            agentPage.value = p;
            loadAgents();
        }
        function changeAgentPageSize(size) {
            agentPageSize.value = size;
            agentPage.value = 1;
            loadAgents();
        }
        function changeSkillPage(p) {
            if (p < 1 || p > skillTotalPages.value) return;
            skillPage.value = p;
            loadSkills();
        }
        function changeSkillPageSize(size) {
            skillPageSize.value = size;
            skillPage.value = 1;
            loadSkills();
        }
        function getAgentPageRange() {
            const p = agentPage.value, total = agentTotalPages.value;
            const start = Math.max(1, p - 2), end = Math.min(total, p + 2);
            const pages = [];
            for (let i = start; i <= end; i++) pages.push(i);
            return pages;
        }
        function getSkillPageRange() {
            const p = skillPage.value, total = skillTotalPages.value;
            const start = Math.max(1, p - 2), end = Math.min(total, p + 2);
            const pages = [];
            for (let i = start; i <= end; i++) pages.push(i);
            return pages;
        }

        // ========================================
        // 提示词管理
        // ========================================
        async function loadPrompts() {
            try {
                let url = `/api/prompts?page=${promptPage.value}&page_size=${promptPageSize.value}`;
                if (promptSearch.value) url += `&keyword=${encodeURIComponent(promptSearch.value)}`;
                const data = await api.get(url);
                if (data.success) {
                    prompts.value = data.data.items || [];
                    promptTotal.value = data.data.total || 0;
                    promptTotalPages.value = data.data.total_pages || 1;
                }
            } catch (e) { showToast('加载提示词失败', 'error'); }
        }

        function openCreatePromptModal() {
            isEditingPrompt.value = false;
            promptForm.id = '';
            promptForm.name = '';
            promptForm.content = '';
            promptForm.description = '';
            promptForm.type = 'private';
            promptForm.is_active = true;
            showCreatePromptModal.value = true;
        }

        async function openEditPromptModal(promptId) {
            try {
                const data = await api.get(`/api/prompts/${promptId}`);
                if (data.success) {
                    const p = data.data;
                    isEditingPrompt.value = true;
                    promptForm.id = p.id;
                    promptForm.name = p.name;
                    promptForm.content = p.content;
                    promptForm.description = p.description || '';
                    promptForm.type = p.type || 'private';
                    promptForm.is_active = p.is_active !== false;
                    showCreatePromptModal.value = true;
                } else { showToast(data.message || '获取失败', 'error'); }
            } catch (e) { showToast('网络错误', 'error'); }
        }

        async function savePrompt() {
            if (!promptForm.name.trim()) { showToast('请输入提示词名称', 'error'); return; }
            if (!promptForm.content.trim()) { showToast('请输入提示词内容', 'error'); return; }
            
            creatingPrompt.value = true;
            try {
                let data;
                if (isEditingPrompt.value) {
                    data = await api.put(`/api/prompts/${promptForm.id}`, {
                        name: promptForm.name,
                        content: promptForm.content,
                        description: promptForm.description,
                        type: promptForm.type,
                        is_active: promptForm.is_active
                    });
                } else {
                    data = await api.post('/api/prompts', {
                        name: promptForm.name,
                        content: promptForm.content,
                        description: promptForm.description,
                        type: promptForm.type,
                        is_active: promptForm.is_active
                    });
                }
                if (data.success) {
                    showCreatePromptModal.value = false;
                    showToast(isEditingPrompt.value ? '保存成功' : '创建成功', 'success');
                    loadPrompts();
                } else { showToast(data.message || data.error || '保存失败', 'error'); }
            } catch (e) { showToast('网络错误', 'error'); }
            finally { creatingPrompt.value = false; }
        }

        async function deletePrompt(promptId) {
            if (!confirm('确定要删除这个提示词吗？')) return;
            try {
                const data = await api.del(`/api/prompts/${promptId}`);
                if (data.success) {
                    showToast('提示词已删除', 'success');
                    loadPrompts();
                } else { showToast(data.message || data.error || '删除失败', 'error'); }
            } catch (e) { showToast('网络错误', 'error'); }
        }

        function changePromptPage(p) {
            if (p < 1 || p > promptTotalPages.value) return;
            promptPage.value = p;
            loadPrompts();
        }

        function changePromptPageSize(size) {
            promptPageSize.value = size;
            promptPage.value = 1;
            loadPrompts();
        }

        function getPromptPageRange() {
            const p = promptPage.value, total = promptTotalPages.value;
            const start = Math.max(1, p - 2), end = Math.min(total, p + 2);
            const pages = [];
            for (let i = start; i <= end; i++) pages.push(i);
            return pages;
        }

        // ========================================
        // 知识库管理
        // ========================================
        async function loadKnowledgeBases() {
            try {
                const data = await api.get('/api/knowledge-bases');
                if (data.success) {
                    knowledgeBases.value = data.data || [];
                }
            } catch (e) { showToast('加载知识库失败', 'error'); }
        }

        function openAddKbModal() {
            isEditingKb.value = false;
            kbForm.id = null;
            kbForm.name = '';
            kbForm.description = '';
            kbForm.embedding_model = '';
            kbForm.type = 'private';
            showKbModal.value = true;
        }

        async function openEditKbModal(kb) {
            isEditingKb.value = true;
            kbForm.id = kb.id;
            kbForm.name = kb.name;
            kbForm.description = kb.description || '';
            kbForm.embedding_model = kb.embedding_model || '';
            kbForm.type = kb.type || 'private';
            showKbModal.value = true;
        }

        async function saveKnowledgeBase() {
            if (!kbForm.name.trim()) { showToast('请输入知识库名称', 'error'); return; }
            try {
                const data = {
                    name: kbForm.name.trim(),
                    description: kbForm.description.trim(),
                    embedding_model: kbForm.embedding_model.trim(),
                    type: kbForm.type
                };
                let result;
                if (isEditingKb.value) {
                    result = await api.put(`/api/knowledge-bases/${kbForm.id}`, data);
                } else {
                    result = await api.post('/api/knowledge-bases', data);
                }
                if (result.success) {
                    showKbModal.value = false;
                    showToast(isEditingKb.value ? '保存成功' : '创建成功', 'success');
                    loadKnowledgeBases();
                } else { showToast(result.message || '保存失败', 'error'); }
            } catch (e) { showToast('网络错误', 'error'); }
        }

        async function deleteKnowledgeBase(kbId) {
            if (!confirm('确定要删除这个知识库吗？')) return;
            try {
                const data = await api.del(`/api/knowledge-bases/${kbId}`);
                if (data.success) {
                    showToast('知识库已删除', 'success');
                    loadKnowledgeBases();
                } else { showToast(data.message || '删除失败', 'error'); }
            } catch (e) { showToast('网络错误', 'error'); }
        }

        async function loadKbDocuments(kbId) {
            try {
                const data = await api.get(`/api/knowledge-bases/${kbId}/documents`);
                if (data.success) {
                    kbDocuments.value = data.data || [];
                }
            } catch (e) { showToast('加载文档失败', 'error'); }
        }

        function openKbDocModal(kbId) {
            kbDocForm.kb_id = kbId;
            kbDocForm.title = '';
            kbDocForm.content = '';
            showKbDocModal.value = true;
        }

        async function saveKbDoc() {
            if (!kbDocForm.title.trim()) { showToast('请输入文档标题', 'error'); return; }
            try {
                const result = await api.post('/api/knowledge-bases/documents', {
                    kb_id: kbDocForm.kb_id,
                    title: kbDocForm.title.trim(),
                    content: kbDocForm.content.trim()
                });
                if (result.success) {
                    showKbDocModal.value = false;
                    showToast('文档创建成功', 'success');
                    loadKbDocuments(kbDocForm.kb_id);
                } else { showToast(result.message || '保存失败', 'error'); }
            } catch (e) { showToast('网络错误', 'error'); }
        }

        async function deleteKbDoc(docId, kbId) {
            if (!confirm('确定要删除这个文档吗？')) return;
            try {
                const data = await api.del(`/api/knowledge-bases/documents/${docId}`);
                if (data.success) {
                    showToast('文档已删除', 'success');
                    loadKbDocuments(kbId);
                } else { showToast(data.message || '删除失败', 'error'); }
            } catch (e) { showToast('网络错误', 'error'); }
        }

        function changeKbPage(p) {
            if (p < 1 || p > kbTotalPages.value) return;
            kbPage.value = p;
            loadKnowledgeBases();
        }

        function changeKbPageSize(size) {
            kbPageSize.value = size;
            kbPage.value = 1;
            loadKnowledgeBases();
        }

        // 知识库详情弹窗
        function openKbDetailModal(kb) {
            currentKb.value = kb;
            kbDetailTab.value = 'upload';
            kbUploadFiles.value = [];
            kbTestQuery.value = '';
            kbTestResults.value = [];
            showKbDetailModal.value = true;
        }

        function handleKbFileSelect(e) {
            const files = Array.from(e.target.files);
            files.forEach(file => {
                kbUploadFiles.value.push({
                    name: file.name,
                    size: file.size,
                    status: 'pending', // pending, uploading, success, error
                    progress: 0,
                    file: file
                });
            });
        }

        function removeKbUploadFile(index) {
            kbUploadFiles.value.splice(index, 1);
        }

        async function uploadKbFiles() {
            const pendingFiles = kbUploadFiles.value.filter(f => f.status === 'pending');
            if (pendingFiles.length === 0) {
                showToast('没有待上传的文件', 'warning');
                return;
            }

            // 构建 FormData，支持多文件批量上传
            const formData = new FormData();
            pendingFiles.forEach(fileItem => {
                formData.append('files', fileItem.file);
            });

            // 将所有待上传文件标记为 uploading
            pendingFiles.forEach(fileItem => {
                fileItem.status = 'uploading';
                fileItem.progress = 30;
            });

            try {
                const response = await fetch('/api/upload/batch', {
                    method: 'POST',
                    headers: auth.getAuthHeaders(),
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    // 标记所有文件为上传成功
                    pendingFiles.forEach(fileItem => {
                        fileItem.progress = 100;
                        fileItem.status = 'success';
                    });
                    const successCount = kbUploadFiles.value.filter(f => f.status === 'success').length;
                    showToast(`成功上传 ${successCount} 个文件`, 'success');
                } else {
                    pendingFiles.forEach(fileItem => {
                        fileItem.status = 'error';
                    });
                    showToast(data.message || '批量上传失败', 'error');
                }
            } catch (e) {
                pendingFiles.forEach(fileItem => {
                    fileItem.status = 'error';
                });
                showToast('批量上传请求失败: ' + e.message, 'error');
            }
        }

        async function testKbRetrieval() {
            if (!kbTestQuery.value.trim()) {
                showToast('请输入测试查询', 'error');
                return;
            }
            kbTestLoading.value = true;
            kbTestResults.value = [];

            try {
                // 模拟命中测试
                await new Promise(resolve => setTimeout(resolve, 1000));
                kbTestResults.value = [
                    { content: '这是知识库中与查询相关的第一个文档片段...', score: 0.95, source: '文档1.pdf' },
                    { content: '这是第二个相关的文档片段，包含一些关键信息...', score: 0.87, source: '文档2.docx' },
                    { content: '这是第三个相关的文档片段...', score: 0.72, source: '文档3.txt' }
                ];
            } catch (e) {
                showToast('测试失败', 'error');
            } finally {
                kbTestLoading.value = false;
            }
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        // ========================================
        // 聊天
        // ========================================
        async function sendMessage() {
            const msg = chatInput.value.trim();
            console.log('sendMessage called:', { msg, hasAgent: !!selectedAgent.value, chatLoading: chatLoading.value });
            if (!msg || !selectedAgent.value || chatLoading.value) {
                console.log('sendMessage blocked:', { noMsg: !msg, noAgent: !selectedAgent.value, isLoading: chatLoading.value });
                return;
            }

            // 构建消息内容，包含文件信息
            let messageContent = msg;
            if (uploadedFiles.value.length > 0) {
                const filePaths = uploadedFiles.value.map(f => f.path).join('\n');
                messageContent = `${msg}\n\n[上传文件]:\n${filePaths}`;
            }

            chatMessages.value.push({ role: 'user', content: msg, time: new Date().toLocaleTimeString() });
            chatInput.value = '';
            chatLoading.value = true;

            // 添加一个空的agent消息占位，后续流式填充
            const agentMsgIdx = chatMessages.value.length;
            chatMessages.value.push({ role: 'agent', content: '', time: new Date().toLocaleTimeString() });

            await nextTick();
            scrollChatToBottom();

            let conversationId = currentConversationId.value;

            // 创建 AbortController 用于终止请求
            chatAbortController = new AbortController();

            try {
                const url = '/api/chat';
                const headers = {
                    'Content-Type': 'application/json',
                    ...auth.getAuthHeaders()
                };
                const response = await fetch(url, {
                    method: 'POST',
                    headers,
                    signal: chatAbortController.signal,
                    body: JSON.stringify({
                        message: messageContent,
                        agent_id: selectedAgent.value.id,
                        conversation_id: conversationId,
                        files: uploadedFiles.value.map(f => ({ name: f.name, path: f.path, size: f.size }))
                    })
                });

                // 发送成功后清空已上传文件列表
                uploadedFiles.value = [];

                if (!response.ok) {
                    chatMessages.value[agentMsgIdx] = {
                        ...chatMessages.value[agentMsgIdx],
                        content: '请求失败，请重试。',
                        role: 'agent error'
                    };
                    return;
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        const trimmed = line.trim();
                        if (!trimmed.startsWith('data: ')) continue;

                        try {
                            const data = JSON.parse(trimmed.slice(6));
                            if (data.type === 'token') {
                                // 使用新对象替换，确保响应式更新
                                chatMessages.value[agentMsgIdx] = {
                                    ...chatMessages.value[agentMsgIdx],
                                    content: chatMessages.value[agentMsgIdx].content + data.content
                                };
                                scrollChatToBottom();
                            } else if (data.type === 'end') {
                                if (data.conversation_id) {
                                    conversationId = data.conversation_id;
                                    currentConversationId.value = data.conversation_id;
                                    setStoredConversationId(selectedAgent.value.id, data.conversation_id);
                                }
                            } else if (data.type === 'error') {
                                chatMessages.value[agentMsgIdx] = {
                                    ...chatMessages.value[agentMsgIdx],
                                    content: data.content || '请求失败，请重试。',
                                    role: 'agent error'
                                };
                            }
                        } catch (e) {
                            // 忽略解析错误
                        }
                    }
                }
            } catch (e) {
                if (e.name === 'AbortError') {
                    // 用户主动终止
                    chatMessages.value[agentMsgIdx] = {
                        ...chatMessages.value[agentMsgIdx],
                        content: chatMessages.value[agentMsgIdx].content + '\n\n[已终止]',
                        role: 'agent'
                    };
                } else {
                    chatMessages.value[agentMsgIdx] = {
                        ...chatMessages.value[agentMsgIdx],
                        content: '网络请求失败，请检查连接。',
                        role: 'agent error'
                    };
                }
            } finally {
                chatLoading.value = false;
                chatAbortController = null;
                await nextTick();
                scrollChatToBottom();
            }
        }

        // 终止当前对话
        function stopChat() {
            console.log('stopChat called:', { hasController: !!chatAbortController });
            if (chatAbortController) {
                chatAbortController.abort();
                chatAbortController = null;
            }
        }

        function onChatKeydown(e) {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
        }

        // 触发文件上传
        function triggerFileUpload() {
            document.getElementById('fileInput').click();
        }

        // 处理文件上传
        async function handleFileUpload(event) {
            const files = event.target.files;
            if (!files || files.length === 0) return;

            isUploading.value = true;

            for (const file of files) {
                try {
                    const formData = new FormData();
                    formData.append('file', file);

                    const response = await fetch('/api/upload', {
                        method: 'POST',
                        headers: auth.getAuthHeaders(),
                        body: formData
                    });

                    const data = await response.json();
                    if (data.success) {
                        uploadedFiles.value.push({
                            name: file.name,
                            path: data.path,
                            size: file.size
                        });
                        showToast(`上传成功: ${file.name}`, 'success');
                    } else {
                        showToast(data.message || `上传失败: ${file.name}`, 'error');
                    }
                } catch (e) {
                    showToast(`上传失败: ${file.name}`, 'error');
                }
            }

            isUploading.value = false;
            // 清空input，允许重复上传相同文件
            event.target.value = '';
        }

        // 移除已上传文件
        function removeUploadedFile(index) {
            uploadedFiles.value.splice(index, 1);
        }

        function scrollChatToBottom() {
            const el = document.getElementById('chatMessages');
            if (el) el.scrollTop = el.scrollHeight;
        }

        // ========================================
        // 执行记录
        // ========================================
        function viewExecution(exec) {
            currentExecution.value = exec;
            showExecutionResultModal.value = true;
        }

        function getAgentName(agentId) {
            return agents.value.find(a => a.id === agentId)?.name || '未知';
        }

        function getSkillName(skillId) {
            const skill = skills.value.find(s => s.id === skillId);
            if (skill) return skill.name;
            // 如果skill不在当前用户的可见列表中，显示ID前8位
            if (skillId && skillId.length > 8) {
                return `Skill(${skillId.slice(0, 8)}...)`;
            }
            return skillId || '未知';
        }

        function getToolName(toolId) {
            const tool = availableTools.value.find(t => t.id === toolId);
            if (tool) return tool.name;
            // 如果tool不在当前用户的可见列表中，显示ID前8位
            if (toolId && toolId.length > 8) {
                return `Tool(${toolId.slice(0, 8)}...)`;
            }
            return toolId || '未知';
        }

        // ========================================
        // 仪表盘
        // ========================================
        async function loadDashboard() {
            dashboardLoading.value = true;
            try {
                const data = await api.get('/api/dashboard/complete');
                console.log('Dashboard data:', data);
                if (data.code === 200) {
                    dashboardData.value = data.data.overview || dashboardData.value;
                    dashboardActivities.value = data.data.recent_activities || [];
                    // 确保 popular 数据结构正确
                    const popular = data.data.popular || {};
                    popularData.value = {
                        popular_agents: popular.popular_agents || [],
                        popular_skills: popular.popular_skills || [],
                        popular_mcps: popular.popular_mcps || []
                    };
                    console.log('Popular data:', popularData.value);
                    dailyStats.value = data.data.daily_stats || [];
                    // 模拟系统运行时间
                    systemUptime.value = calculateUptime();
                    // 更新图表 - 延迟确保 DOM 已准备好
                    setTimeout(() => {
                        nextTick(() => {
                            initCharts();
                        });
                    }, 100);
                } else {
                    showToast(data.message || '加载仪表盘数据失败', 'error');
                }
            } catch (e) {
                console.error('Dashboard load error:', e);
                showToast('加载仪表盘数据失败', 'error');
            } finally {
                dashboardLoading.value = false;
            }
        }

        // ECharts 实例
        let pieChartInstance = null;
        let lineChartInstance = null;
        let chartInitRetryCount = 0;
        const MAX_RETRY = 5;

        function initCharts() {
            if (currentPage.value !== 'dashboard') return;
            
            try {
                // 先销毁旧实例（如果存在）
                if (pieChartInstance) {
                    pieChartInstance.dispose();
                    pieChartInstance = null;
                }
                if (lineChartInstance) {
                    lineChartInstance.dispose();
                    lineChartInstance = null;
                }
                
                let pieInitialized = false;
                let lineInitialized = false;
                
                // 初始化饼图
                if (typeof echarts !== 'undefined') {
                    const pieDom = document.querySelector('.echart-container');
                    if (pieDom) {
                        pieChartInstance = echarts.init(pieDom);
                        pieInitialized = true;
                        updatePieChart();
                    }
                }

                // 初始化折线图
                if (typeof echarts !== 'undefined') {
                    const lineDoms = document.querySelectorAll('.echart-container');
                    if (lineDoms.length > 1) {
                        lineChartInstance = echarts.init(lineDoms[1]);
                        lineInitialized = true;
                        updateLineChart();
                    }
                }
                
                console.log('Charts initialized:', { pie: pieInitialized, line: lineInitialized });
                
                // 如果初始化失败且未达到最大重试次数，延迟重试
                if ((!pieChartInstance || !lineChartInstance) && chartInitRetryCount < MAX_RETRY) {
                    chartInitRetryCount++;
                    console.log(`Chart init retry ${chartInitRetryCount}/${MAX_RETRY}`);
                    setTimeout(() => {
                        initCharts();
                    }, 300);
                } else {
                    chartInitRetryCount = 0;
                }
            } catch (e) {
                console.error('Charts init error:', e);
                if (chartInitRetryCount < MAX_RETRY) {
                    chartInitRetryCount++;
                    setTimeout(() => {
                        initCharts();
                    }, 300);
                }
            }
        }

        function updatePieChart() {
            if (!pieChartInstance) return;
            
            const option = {
                tooltip: {
                    trigger: 'item',
                    formatter: '{b}: {c} ({d}%)'
                },
                legend: {
                    bottom: '5%',
                    left: 'center'
                },
                color: ['#667eea', '#f5576c', '#4facfe'],
                series: [
                    {
                        name: '资源分布',
                        type: 'pie',
                        radius: ['40%', '70%'],
                        avoidLabelOverlap: false,
                        itemStyle: {
                            borderRadius: 10,
                            borderColor: '#fff',
                            borderWidth: 2
                        },
                        label: {
                            show: false,
                            position: 'center'
                        },
                        emphasis: {
                            label: {
                                show: true,
                                fontSize: 20,
                                fontWeight: 'bold'
                            }
                        },
                        labelLine: {
                            show: false
                        },
                        data: [
                            { value: dashboardData.value.agents.total, name: '智能体' },
                            { value: dashboardData.value.skills.total, name: '技能' },
                            { value: dashboardData.value.mcps.total, name: 'MCP' }
                        ]
                    }
                ]
            };
            pieChartInstance.setOption(option);
        }

        function updateLineChart() {
            if (!lineChartInstance) return;
            
            const dates = dailyStats.value.map(d => d.date);
            const chatCounts = dailyStats.value.map(d => d.chat_count);
            
            const option = {
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {
                        type: 'cross',
                        label: {
                            backgroundColor: '#6a7985'
                        }
                    }
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '3%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    boundaryGap: false,
                    data: dates,
                    axisLine: {
                        lineStyle: {
                            color: '#999'
                        }
                    }
                },
                yAxis: {
                    type: 'value',
                    axisLine: {
                        lineStyle: {
                            color: '#999'
                        }
                    },
                    splitLine: {
                        lineStyle: {
                            color: '#eee'
                        }
                    }
                },
                series: [
                    {
                        name: '消息数',
                        type: 'line',
                        stack: 'Total',
                        smooth: true,
                        lineStyle: {
                            width: 3,
                            color: '#667eea'
                        },
                        showSymbol: false,
                        areaStyle: {
                            opacity: 0.8,
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: 'rgba(102, 126, 234, 0.4)' },
                                { offset: 1, color: 'rgba(102, 126, 234, 0.05)' }
                            ])
                        },
                        emphasis: {
                            focus: 'series'
                        },
                        data: chatCounts
                    }
                ]
            };
            lineChartInstance.setOption(option);
        }

        function resizeCharts() {
            if (pieChartInstance) pieChartInstance.resize();
            if (lineChartInstance) lineChartInstance.resize();
        }

        function calculateUptime() {
            // 模拟从某个固定时间开始的运行时间
            const startTime = new Date('2024-01-01').getTime();
            const now = Date.now();
            const diff = now - startTime;
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            return `${days}天 ${hours}小时`;
        }

        function calculateRate(part, total) {
            if (!total) return 0;
            return Math.round((part / total) * 100);
        }

        // 饼图计算
        function getPieSlice(value) {
            const total = dashboardData.value.agents.total + dashboardData.value.skills.total + dashboardData.value.mcps.total;
            if (!total) return 0;
            return (value / total) * 502; // 502是圆周长 (2 * PI * 80)
        }

        function calculateResourcePercent(value) {
            const total = dashboardData.value.agents.total + dashboardData.value.skills.total + dashboardData.value.mcps.total;
            if (!total) return 0;
            return Math.round((value / total) * 100);
        }

        // 对话趋势数据（使用dailyStats）
        const chatTrendData = computed(() => {
            return dailyStats.value.map(day => ({
                label: day.date,
                value: day.chat_count
            }));
        });

        function getMaxChatValue() {
            if (!chatTrendData.value.length) return 100;
            return Math.max(...chatTrendData.value.map(d => d.value), 10);
        }

        function getChatLinePath() {
            if (!chatTrendData.value.length) return '';
            const max = getMaxChatValue();
            const width = 400;
            const height = 150;
            const points = chatTrendData.value.map((point, index) => {
                const x = (index / (chatTrendData.value.length - 1)) * width;
                const y = height - (point.value / max) * height;
                return `${x},${y}`;
            });
            return `M ${points.join(' L ')}`;
        }

        function getChatAreaPath() {
            if (!chatTrendData.value.length) return '';
            const linePath = getChatLinePath();
            if (!linePath) return '';
            return `${linePath} L 400,150 L 0,150 Z`;
        }

        function getMaxMessageCount() {
            if (!popularData.value.popular_agents || !popularData.value.popular_agents.length) return 1;
            return Math.max(...popularData.value.popular_agents.map(a => a.message_count || 0), 1);
        }

        function getMaxAgentCount() {
            if (!popularData.value.popular_skills || !popularData.value.popular_skills.length) return 1;
            return Math.max(...popularData.value.popular_skills.map(s => s.agent_count || 0), 1);
        }

        function getActivityIcon(type) {
            const iconMap = {
                'agent_create': 'plus',
                'agent_update': 'edit',
                'agent_delete': 'trash',
                'skill_create': 'plus',
                'skill_update': 'edit',
                'skill_delete': 'trash',
                'mcp_create': 'plus',
                'mcp_update': 'edit',
                'mcp_delete': 'trash',
                'user_login': 'user',
                'user_logout': 'logout',
                'chat': 'message',
                'execution': 'play'
            };
            return iconMap[type] || 'info-circle';
        }

        function formatTime(timeStr) {
            if (!timeStr) return '';
            const date = new Date(timeStr);
            const now = new Date();
            const diff = now - date;
            const minutes = Math.floor(diff / 60000);
            const hours = Math.floor(diff / 3600000);
            const days = Math.floor(diff / 86400000);

            if (minutes < 1) return '刚刚';
            if (minutes < 60) return `${minutes}分钟前`;
            if (hours < 24) return `${hours}小时前`;
            if (days < 7) return `${days}天前`;
            return date.toLocaleDateString('zh-CN');
        }

        // ========================================
        // MCP 管理
        // ========================================
        async function loadMcps() {
            try {
                console.log('Loading MCPs...');
                const data = await api.get(`/api/mcps?page=${mcpPage.value}&page_size=${mcpPageSize.value}`);
                console.log('MCP API response:', data);
                if (data.code === 200) {
                    mcpServers.value = data.data.items || [];
                    mcpTotal.value = data.data.total || 0;
                    mcpTotalPages.value = data.data.total_pages || 0;
                    console.log('MCPs loaded:', mcpServers.value);
                } else {
                    console.error('MCP API error:', data.message);
                    showToast(data.message || '加载MCP列表失败', 'error');
                    mcpServers.value = [];
                }
            } catch (e) {
                console.error('MCP load exception:', e);
                showToast('加载MCP列表失败', 'error');
                mcpServers.value = [];
            }
        }
        function changeMcpPage(page) {
            mcpPage.value = page;
            loadMcps();
        }
        function changeMcpPageSize(size) {
            mcpPageSize.value = size;
            mcpPage.value = 1;
            loadMcps();
        }
        function openAddMcpModal() {
            isEditingMcp.value = false;
            mcpForm.id = null; mcpForm.name = ''; mcpForm.type = 'sse'; mcpForm.endpoint = ''; mcpForm.visibility = 'private'; mcpForm.description = '';
            showMcpModal.value = true;
        }
        function openEditMcpModal(id) {
            const server = mcpServers.value.find(s => s.id === id);
            if (!server) return;
            isEditingMcp.value = true;
            mcpForm.id = server.id; mcpForm.name = server.name; mcpForm.type = server.type;
            mcpForm.endpoint = server.endpoint; mcpForm.visibility = server.visibility || 'private'; mcpForm.description = server.description || '';
            showMcpModal.value = true;
        }
        async function saveMcpServer() {
            if (!mcpForm.name.trim() || !mcpForm.endpoint.trim()) { showToast('请填写服务名称和端点', 'error'); return; }
            try {
                if (isEditingMcp.value) {
                    const data = await api.put(`/api/mcps/${mcpForm.id}`, {
                        name: mcpForm.name,
                        type: mcpForm.type,
                        endpoint: mcpForm.endpoint,
                        visibility: mcpForm.visibility,
                        description: mcpForm.description
                    });
                    if (data.code === 200) {
                        showToast('MCP服务已更新', 'success');
                        loadMcps();
                    } else {
                        showToast(data.message || '更新失败', 'error');
                    }
                } else {
                    const data = await api.post('/api/mcps', {
                        name: mcpForm.name,
                        type: mcpForm.type,
                        endpoint: mcpForm.endpoint,
                        visibility: mcpForm.visibility,
                        description: mcpForm.description
                    });
                    if (data.code === 200) {
                        showToast('MCP服务已添加', 'success');
                        loadMcps();
                    } else {
                        showToast(data.message || '添加失败', 'error');
                    }
                }
                showMcpModal.value = false;
            } catch (e) {
                showToast('操作失败', 'error');
            }
        }
        async function deleteMcpServer(id) {
            if (!confirm('确定要删除此MCP服务吗？')) return;
            try {
                const data = await api.request(`/api/mcps/${id}`, { method: 'DELETE' });
                if (data.code === 200) {
                    showToast('MCP服务已删除', 'success');
                    loadMcps();
                } else {
                    showToast(data.message || '删除失败', 'error');
                }
            } catch (e) {
                showToast('删除失败', 'error');
            }
        }
        function getMcpStatusIcon(status) {
              return status === 'active' ? 'icon-check-circle' : 'icon-stop-circle';
          }
          async function toggleMcpStatus(id) {
              const server = mcpServers.value.find(s => s.id === id);
              if (!server) return;
              const newStatus = server.status === 'active' ? 'stopped' : 'active';
              try {
                  const data = await api.put(`/api/mcps/${id}`, { status: newStatus });
                  if (data.code === 200) {
                      server.status = newStatus;
                      showToast(newStatus === 'active' ? 'MCP服务已启动' : 'MCP服务已停止', 'success');
                  } else {
                      showToast(data.message || '操作失败', 'error');
                  }
              } catch (e) {
                  showToast('操作失败', 'error');
              }
          }
          async function syncMcpTools(id) {
              syncingMcpId.value = id;
              try {
                  const data = await api.post(`/api/mcps/${id}/sync`, {});
                  if (data.code === 200) {
                      showToast(data.message || '同步成功', 'success');
                      // 更新MCP状态
                      const server = mcpServers.value.find(s => s.id === id);
                      if (server) {
                          server.status = 'active';
                      }
                      // 如果当前选中了该MCP，刷新工具列表
                      if (selectedMcpId.value === id) {
                          await loadMcpTools(id);
                      }
                  } else {
                      showToast(data.message || '同步失败', 'error');
                      // 更新MCP状态
                      const server = mcpServers.value.find(s => s.id === id);
                      if (server) {
                          server.status = 'stopped';
                      }
                  }
              } catch (e) {
                  showToast('同步失败', 'error');
              } finally {
                  syncingMcpId.value = null;
              }
          }
          async function selectMcpServer(id) {
              selectedMcpId.value = id;
              await loadMcpTools(id);
          }
          async function loadMcpTools(mcpId) {
              try {
                  const data = await api.get(`/api/mcps/${mcpId}/tools`);
                  console.log('Loaded MCP tools:', data);
                  if (data.code === 200) {
                      mcpTools.value = data.data.tools || [];
                  } else {
                      showToast(data.message || '加载工具列表失败', 'error');
                      mcpTools.value = [];
                  }
              } catch (e) {
                  showToast('加载工具列表失败', 'error');
                  mcpTools.value = [];
              }
          }
          async function openToolDebugModal(tool) {
              // 解析参数（后端返回的可能是 JSON 字符串）
              let params = tool.parameters;
              if (typeof params === 'string') {
                  try {
                      params = JSON.parse(params.replace(/'/g, '"'));
                  } catch (e) {
                      console.error('Failed to parse parameters:', e);
                      params = {};
                  }
              }
              // 先关闭弹窗，确保重新渲染
              showToolDebugModal.value = false;
              await nextTick();
              // 设置数据
              debugTool.name = tool.name || '';
              debugTool.description = tool.description || '';
              debugTool.parameters = params || {};
              debugToolResult.value = null;
              showToolDebugModal.value = true;
          }
          function closeToolDebugModal() {
              showToolDebugModal.value = false;
              Object.assign(debugTool, { name: '', description: '', parameters: {} });
              debugToolResult.value = null;
          }

          function hasToolParameters() {
              const params = debugTool.parameters;
              console.log('hasToolParameters check:', params);
              if (!params) return false;
              if (params.properties && typeof params.properties === 'object') {
                  const keys = Object.keys(params.properties);
                  console.log('Param keys:', keys);
                  return keys.length > 0;
              }
              return false;
          }
          function getToolParamKeys() {
              const params = debugTool.parameters;
              if (params && params.properties && typeof params.properties === 'object') {
                  return Object.keys(params.properties);
              }
              return [];
          }
          async function invokeTool() {
              if (!selectedMcpId.value || !debugTool.name) return;
              invokingTool.value = true;
              try {
                  // 构建参数对象
                  const params = {};
                  const schema = debugTool.parameters;
                  if (schema && schema.properties) {
                      for (const [key, prop] of Object.entries(schema.properties)) {
                          const inputEl = document.querySelector(`[data-tool-param="${key}"]`);
                          if (inputEl) {
                              params[key] = inputEl.value;
                          }
                      }
                  }

                  const data = await api.post(`/api/mcps/${selectedMcpId.value}/tools/${debugTool.name}/invoke`, {
                      parameters: params
                  });
                  
                  if (data.code === 200) {
                      debugToolResult.value = data.data.result;
                      showToast('调用成功', 'success');
                  } else {
                      showToast(data.message || '调用失败', 'error');
                      debugToolResult.value = { error: data.message };
                  }
              } catch (e) {
                  showToast('调用失败', 'error');
                  debugToolResult.value = { error: e.message };
              } finally {
                  invokingTool.value = false;
              }
          }

        // ========================================
        // 模型管理
        // ========================================
        async function loadModels() {
             try {
                 const res = await fetch(`/api/models?page=${modelPage.value}&page_size=${modelPageSize.value}`);
                 const data = await res.json();
                 if (data.code === 200) {
                     models.value = data.data.items || [];
                     modelTotal.value = data.data.total || 0;
                     modelTotalPages.value = data.data.total_pages || 0;
                 } else {
                     showToast(data.message || '加载模型列表失败', 'error');
                     models.value = [];
                 }
             } catch (e) {
                 showToast('加载模型列表失败', 'error');
                 models.value = [];
             }
         }
         function changeModelPage(page) {
             modelPage.value = page;
             loadModels();
         }
         function changeModelPageSize(size) {
             modelPageSize.value = size;
             modelPage.value = 1;
             loadModels();
         }
        function openAddModelModal() {
            isEditingModel.value = false;
            modelForm.id = null;
            modelForm.name = '';
            modelForm.modelType = 'chat';
            modelForm.provider = 'openai';
            modelForm.modelName = '';
            modelForm.baseUrl = '';
            modelForm.apiKey = '';
            modelForm.description = '';
            showModelModal.value = true;
        }
        function openEditModelModal(id) {
            const mdl = models.value.find(m => m.id === id);
            if (!mdl) return;
            isEditingModel.value = true;
            Object.assign(modelForm, {
                id: mdl.id,
                name: mdl.name,
                modelType: mdl.modelType || 'chat',
                provider: mdl.provider,
                modelName: mdl.modelName,
                baseUrl: mdl.baseUrl,
                apiKey: mdl.apiKey || '',
                description: mdl.description || ''
            });
            showModelModal.value = true;
        }
        async function saveModel() {
            if (!modelForm.name.trim() || !modelForm.modelName.trim()) {
                showToast('请填写显示名称和模型ID', 'error');
                return;
            }
            const payload = {
                name: modelForm.name,
                modelType: modelForm.modelType,
                provider: modelForm.provider,
                modelName: modelForm.modelName,
                baseUrl: modelForm.baseUrl,
                apiKey: modelForm.apiKey,
                description: modelForm.description
            };
            try {
                if (isEditingModel.value) {
                     const res = await fetch(`/api/models/${modelForm.id}`, {
                         method: 'PUT',
                         headers: { 'Content-Type': 'application/json' },
                         body: JSON.stringify(payload)
                     });
                     const data = await res.json();
                     if (data.code === 200) {
                         showToast('模型已更新', 'success');
                         await loadModels();
                         showModelModal.value = false;
                     } else {
                         showToast(data.message || '更新失败', 'error');
                     }
                 } else {
                     const res = await fetch('/api/models', {
                         method: 'POST',
                         headers: { 'Content-Type': 'application/json' },
                         body: JSON.stringify(payload)
                     });
                     const data = await res.json();
                     if (data.code === 200) {
                         showToast('模型已添加', 'success');
                         await loadModels();
                         showModelModal.value = false;
                     } else {
                         showToast(data.message || '添加失败', 'error');
                     }
                 }
            } catch (e) {
                showToast('保存失败', 'error');
            }
        }
        async function deleteModel(id) {
             if (!confirm('确定要删除此模型配置吗？')) return;
             try {
                 const res = await fetch(`/api/models/${id}`, { method: 'DELETE' });
                 const data = await res.json();
                 if (data.code === 200) {
                     showToast('模型已删除', 'success');
                     await loadModels();
                 } else {
                     showToast(data.message || '删除失败', 'error');
                 }
             } catch (e) {
                 showToast('删除失败', 'error');
             }
         }

        async function testModelConnection(modelId) {
            testingModelId.value = modelId;
            try {
                const data = await api.post(`/api/models/${modelId}/test`, {});
                if (data.code === 200) {
                    showToast('连接成功', 'success');
                    // 更新模型状态
                    const model = models.value.find(m => m.id === modelId);
                    if (model) {
                        model.status = data.data.status;
                    }
                } else {
                    showToast(data.message || '连接失败', 'error');
                    // 更新模型状态
                    const model = models.value.find(m => m.id === modelId);
                    if (model) {
                        model.status = 'stopped';
                    }
                }
            } catch (e) {
                showToast('测试连接失败', 'error');
            } finally {
                testingModelId.value = null;
            }
        }


        // ========================================
        // 权限管控 - 部门管理
        // ========================================
        async function loadDepartments() {
            try {
                const result = await api.get('/api/departments');
                if (result.success) {
                    departments.value = result.data || [];
                }
            } catch (e) {
                showToast('加载部门列表失败', 'error');
            }
        }

        async function loadDepartmentTree() {
            try {
                const result = await api.get('/api/departments/tree');
                if (result.success) {
                    departmentTree.value = result.data || [];
                }
            } catch (e) {
                showToast('加载部门树失败', 'error');
            }
        }

        function openAddDepartmentModal() {
            isEditingDepartment.value = false;
            departmentForm.id = null;
            departmentForm.name = '';
            departmentForm.code = '';
            departmentForm.parent_id = '';
            departmentForm.description = '';
            departmentForm.sort_order = 0;
            departmentForm.status = 'active';
            showDepartmentModal.value = true;
        }

        function openEditDepartmentModal(dept) {
            isEditingDepartment.value = true;
            departmentForm.id = dept.id;
            departmentForm.name = dept.name;
            departmentForm.code = dept.code;
            departmentForm.parent_id = dept.parent_id || '';
            departmentForm.description = dept.description || '';
            departmentForm.sort_order = dept.sort_order || 0;
            departmentForm.status = dept.status;
            showDepartmentModal.value = true;
        }

        async function saveDepartment() {
            if (!departmentForm.name.trim() || !departmentForm.code.trim()) {
                showToast('请填写部门名称和编码', 'error');
                return;
            }

            try {
                if (isEditingDepartment.value) {
                    const result = await api.put(`/api/departments/${departmentForm.id}`, {
                        name: departmentForm.name,
                        code: departmentForm.code,
                        parent_id: departmentForm.parent_id || null,
                        description: departmentForm.description,
                        sort_order: departmentForm.sort_order,
                        status: departmentForm.status
                    });
                    if (result.success) {
                        showToast('部门已更新', 'success');
                        await loadDepartments();
                        await loadDepartmentTree();
                        showDepartmentModal.value = false;
                    } else {
                        showToast(result.message || '更新失败', 'error');
                    }
                } else {
                    const result = await api.post('/api/departments', {
                        name: departmentForm.name,
                        code: departmentForm.code,
                        parent_id: departmentForm.parent_id || null,
                        description: departmentForm.description,
                        sort_order: departmentForm.sort_order,
                        status: departmentForm.status
                    });
                    if (result.success) {
                        showToast('部门已添加', 'success');
                        await loadDepartments();
                        await loadDepartmentTree();
                        showDepartmentModal.value = false;
                    } else {
                        showToast(result.message || '创建失败', 'error');
                    }
                }
            } catch (e) {
                showToast(e.message || '保存失败', 'error');
            }
        }

        async function deleteDepartment(id) {
            if (!confirm('确定要删除此部门吗？')) return;
            try {
                const result = await api.del(`/api/departments/${id}`);
                if (result.success) {
                    showToast('部门已删除', 'success');
                    await loadDepartments();
                    await loadDepartmentTree();
                } else {
                    showToast(result.message || '删除失败', 'error');
                }
            } catch (e) {
                showToast(e.message || '删除失败', 'error');
            }
        }

        // ========================================
        // 权限管控 - 用户管理
        // ========================================
        async function loadPermissionUsers() {
            try {
                const result = await api.get('/api/users');
                if (result.success) {
                    permissionUsers.value = result.data.map(u => ({
                        id: u.id,
                        username: u.username,
                        email: u.email,
                        real_name: u.real_name,
                        phone: u.phone,
                        department_id: u.department_id,
                        department_name: u.department_name,
                        roles: u.roles || [],
                        role_ids: u.role_ids || [],
                        status: u.status,
                        created_at: u.created_at ? u.created_at.slice(0, 10) : ''
                    }));
                }
            } catch (e) {
                showToast('加载用户列表失败', 'error');
            }
        }

        function openAddUserModal() {
            isEditingUser.value = false;
            userForm.id = null;
            userForm.username = '';
            userForm.email = '';
            userForm.real_name = '';
            userForm.phone = '';
            userForm.department_id = '';
            userForm.role_ids = [];
            userForm.status = 'active';
            userForm.password = '';
            showUserModal.value = true;
        }

        function openEditUserModal(user) {
            isEditingUser.value = true;
            userForm.id = user.id;
            userForm.username = user.username;
            userForm.email = user.email;
            userForm.real_name = user.real_name || '';
            userForm.phone = user.phone || '';
            userForm.department_id = user.department_id || '';
            userForm.role_ids = user.role_ids || [];
            userForm.status = user.status;
            userForm.password = '';
            showUserModal.value = true;
        }

        async function saveUser() {
            if (!userForm.username.trim()) {
                showToast('请填写用户名', 'error');
                return;
            }
            if (!isEditingUser.value && !userForm.password) {
                showToast('请填写密码', 'error');
                return;
            }

            try {
                const data = {
                    username: userForm.username,
                    email: userForm.email,
                    real_name: userForm.real_name,
                    phone: userForm.phone,
                    department_id: userForm.department_id || null,
                    role_ids: userForm.role_ids,
                    status: userForm.status
                };
                if (userForm.password) {
                    data.password = userForm.password;
                }

                if (isEditingUser.value) {
                    const result = await api.put(`/api/users/${userForm.id}`, data);
                    if (result.success) {
                        showToast('用户已更新', 'success');
                        await loadPermissionUsers();
                        showUserModal.value = false;
                    } else {
                        showToast(result.message || '更新失败', 'error');
                    }
                } else {
                    const result = await api.post('/api/users', data);
                    if (result.success) {
                        showToast('用户已添加', 'success');
                        await loadPermissionUsers();
                        showUserModal.value = false;
                    } else {
                        showToast(result.message || '创建失败', 'error');
                    }
                }
            } catch (e) {
                showToast(e.message || '保存失败', 'error');
            }
        }

        async function deleteUser(id) {
            if (!confirm('确定要删除此用户吗？')) return;
            try {
                const result = await api.del(`/api/users/${id}`);
                if (result.success) {
                    showToast('用户已删除', 'success');
                    await loadPermissionUsers();
                } else {
                    showToast(result.message || '删除失败', 'error');
                }
            } catch (e) {
                showToast(e.message || '删除失败', 'error');
            }
        }

        // ========================================
        // 权限管控 - 角色管理
        // ========================================
        async function loadPermissionRoles() {
            try {
                const result = await api.get('/api/roles');
                if (result.success) {
                    permissionRoles.value = result.data.map(r => ({
                        id: r.id,
                        name: r.name,
                        code: r.code,
                        description: r.description,
                        permission_ids: r.permission_ids || [],
                        status: r.status,
                        created_at: r.created_at ? r.created_at.slice(0, 10) : ''
                    }));
                }
            } catch (e) {
                showToast('加载角色列表失败', 'error');
            }
        }

        function openAddRoleModal() {
            isEditingRole.value = false;
            roleForm.id = null;
            roleForm.name = '';
            roleForm.code = '';
            roleForm.description = '';
            roleForm.permission_ids = [];
            roleForm.status = 'active';
            showRoleModal.value = true;
        }

        function openEditRoleModal(role) {
            isEditingRole.value = true;
            roleForm.id = role.id;
            roleForm.name = role.name;
            roleForm.code = role.code;
            roleForm.description = role.description || '';
            roleForm.permission_ids = role.permission_ids || [];
            roleForm.status = role.status;
            showRoleModal.value = true;
        }

        function toggleRolePermission(permId) {
            const idx = roleForm.permission_ids.indexOf(permId);
            if (idx > -1) {
                roleForm.permission_ids.splice(idx, 1);
            } else {
                roleForm.permission_ids.push(permId);
            }
        }

        async function saveRole() {
            if (!roleForm.name.trim() || !roleForm.code.trim()) {
                showToast('请填写角色名称和编码', 'error');
                return;
            }

            try {
                const data = {
                    name: roleForm.name,
                    code: roleForm.code,
                    description: roleForm.description,
                    permission_ids: roleForm.permission_ids,
                    status: roleForm.status
                };

                if (isEditingRole.value) {
                    const result = await api.put(`/api/roles/${roleForm.id}`, data);
                    if (result.success) {
                        showToast('角色已更新', 'success');
                        await loadPermissionRoles();
                        showRoleModal.value = false;
                    } else {
                        showToast(result.message || '更新失败', 'error');
                    }
                } else {
                    const result = await api.post('/api/roles', data);
                    if (result.success) {
                        showToast('角色已添加', 'success');
                        await loadPermissionRoles();
                        showRoleModal.value = false;
                    } else {
                        showToast(result.message || '创建失败', 'error');
                    }
                }
            } catch (e) {
                showToast(e.message || '保存失败', 'error');
            }
        }

        async function deleteRole(id) {
            if (!confirm('确定要删除此角色吗？')) return;
            try {
                const result = await api.del(`/api/roles/${id}`);
                if (result.success) {
                    showToast('角色已删除', 'success');
                    await loadPermissionRoles();
                } else {
                    showToast(result.message || '删除失败', 'error');
                }
            } catch (e) {
                showToast(e.message || '删除失败', 'error');
            }
        }

        // ========================================
        // 权限管控 - 权限管理
        // ========================================
        async function loadAllPermissions() {
            try {
                const result = await api.get('/api/permissions');
                if (result.success) {
                    allPermissions.value = result.data || [];
                }
            } catch (e) {
                showToast('加载权限列表失败', 'error');
            }
        }

        async function loadUserMenus() {
            try {
                const result = await api.get('/api/permissions/menus');
                if (result.success) {
                    userMenus.value = result.data || [];
                }
            } catch (e) {
                console.error('加载用户菜单失败:', e);
            }
        }

        function openAddPermissionModal() {
            isEditingPermission.value = false;
            permissionForm.id = null;
            permissionForm.key = '';
            permissionForm.name = '';
            permissionForm.is_menu = false;
            permissionForm.menu_path = '';
            permissionForm.menu_icon = '';
            permissionForm.menu_order = 0;
            permissionForm.status = true;
            showPermissionModal.value = true;
        }

        function openEditPermissionModal(perm) {
            isEditingPermission.value = true;
            permissionForm.id = perm.id;
            permissionForm.key = perm.key;
            permissionForm.name = perm.name;
            permissionForm.is_menu = perm.is_menu || false;
            permissionForm.menu_path = perm.menu_path || '';
            permissionForm.menu_icon = perm.menu_icon || '';
            permissionForm.menu_order = perm.menu_order || 0;
            permissionForm.status = perm.status === 'active';
            showPermissionModal.value = true;
        }

        async function savePermission() {
            if (!permissionForm.key.trim() || !permissionForm.name.trim()) {
                showToast('权限标识和名称不能为空', 'error');
                return;
            }

            try {
                const data = {
                    key: permissionForm.key.trim(),
                    name: permissionForm.name.trim(),
                    is_menu: permissionForm.is_menu,
                    menu_path: permissionForm.is_menu ? permissionForm.menu_path.trim() : null,
                    menu_icon: permissionForm.is_menu ? permissionForm.menu_icon.trim() : null,
                    menu_order: permissionForm.is_menu ? parseInt(permissionForm.menu_order) || 0 : 0,
                    status: permissionForm.status
                };

                if (isEditingPermission.value) {
                    const result = await api.put(`/api/permissions/${permissionForm.id}`, data);
                    if (result.success) {
                        showToast('权限更新成功', 'success');
                        showPermissionModal.value = false;
                        await loadAllPermissions();
                    } else {
                        showToast(result.message || '更新失败', 'error');
                    }
                } else {
                    const result = await api.post('/api/permissions', data);
                    if (result.success) {
                        showToast('权限创建成功', 'success');
                        showPermissionModal.value = false;
                        await loadAllPermissions();
                    } else {
                        showToast(result.message || '创建失败', 'error');
                    }
                }
            } catch (e) {
                showToast(e.message || '操作失败', 'error');
            }
        }

        async function deletePermission(id) {
            if (!confirm('确定要删除此权限吗？删除后相关角色的权限配置也会受影响。')) return;

            try {
                const result = await api.del(`/api/permissions/${id}`);
                if (result.success) {
                    showToast('权限删除成功', 'success');
                    await loadAllPermissions();
                } else {
                    showToast(result.message || '删除失败', 'error');
                }
            } catch (e) {
                showToast(e.message || '删除失败', 'error');
            }
        }

        async function initDefaultPermissions() {
            try {
                const result = await api.post('/api/permissions/init', {});
                if (result.success) {
                    showToast(result.message, 'success');
                    await loadAllPermissions();
                    await loadPermissionTree();
                } else {
                    showToast(result.message || '初始化失败', 'error');
                }
            } catch (e) {
                showToast(e.message || '初始化失败', 'error');
            }
        }

        function getPermissionLabel(key) {
            const p = allPermissions.value.find(x => x.key === key);
            return p ? p.label : key;
        }

        function getDepartmentName(deptId) {
            const dept = departments.value.find(d => d.id === deptId);
            return dept ? dept.name : '-';
        }

        function getRoleNames(roleIds) {
            if (!roleIds || roleIds.length === 0) return '-';
            return roleIds.map(id => {
                const role = permissionRoles.value.find(r => r.id === id);
                return role ? role.name : id;
            }).join(', ');
        }



        // ========================================
        // 登录/登出
        // ========================================
        async function handleLogin() {
            if (!loginForm.username.trim() || !loginForm.password.trim()) {
                loginError.value = '请输入用户名和密码';
                return;
            }
            loginLoading.value = true;
            loginError.value = '';
            try {
                const result = await api.post('/api/auth/login', {
                    username: loginForm.username.trim(),
                    password: loginForm.password.trim()
                });
                if (result.success && result.data) {
                    auth.setAuth(result.data.token, result.data);
                    isLoggedIn.value = true;
                    currentUser.value = result.data;
                    token.value = result.data.token;
                    showToast('登录成功', 'success');
                    // 加载用户菜单
                    await loadUserMenus();
                    loadAgents();
                    loadSkills();
                } else {
                    loginError.value = result.message || '登录失败';
                }
            } catch (e) {
                loginError.value = '网络错误，请稍后重试';
            } finally {
                loginLoading.value = false;
            }
        }

        async function handleLogout() {
            try {
                await api.post('/api/auth/logout', {});
            } catch (e) {}
            auth.clearAuth();
            isLoggedIn.value = false;
            currentUser.value = null;
            token.value = null;
            loginForm.username = '';
            loginForm.password = '';
            // 清除智能体和技能相关状态
            selectedAgent.value = null;
            showSettingsPanel.value = false;
            agents.value = [];
            skills.value = [];
            showToast('已退出登录', 'info');
        }

        async function checkAuth() {
            if (!auth.isLoggedIn()) return;
            try {
                const result = await api.get('/api/auth/verify');
                if (result.authenticated) {
                    isLoggedIn.value = true;
                    // 使用验证返回的最新用户数据
                    if (result.data) {
                        auth.user = result.data;
                        localStorage.setItem('auth_user', JSON.stringify(result.data));
                    }
                    currentUser.value = auth.user;
                    token.value = auth.token;
                } else {
                    auth.clearAuth();
                    isLoggedIn.value = false;
                    currentUser.value = null;
                    token.value = null;
                }
            } catch (e) {
                auth.clearAuth();
                isLoggedIn.value = false;
                currentUser.value = null;
                token.value = null;
            }
        }

        // 修改密码
        async function handleChangePassword() {
            changePasswordError.value = '';

            if (!changePasswordForm.oldPassword || !changePasswordForm.newPassword || !changePasswordForm.confirmPassword) {
                changePasswordError.value = '请填写所有字段';
                return;
            }

            if (changePasswordForm.newPassword.length < 6) {
                changePasswordError.value = '新密码长度不能少于6位';
                return;
            }

            if (changePasswordForm.newPassword !== changePasswordForm.confirmPassword) {
                changePasswordError.value = '两次输入的新密码不一致';
                return;
            }

            changePasswordLoading.value = true;
            try {
                const result = await api.post('/api/auth/change-password', {
                    old_password: changePasswordForm.oldPassword,
                    new_password: changePasswordForm.newPassword
                });

                if (result.success) {
                    showToast('密码修改成功', 'success');
                    showChangePasswordModal.value = false;
                    changePasswordForm.oldPassword = '';
                    changePasswordForm.newPassword = '';
                    changePasswordForm.confirmPassword = '';
                } else {
                    changePasswordError.value = result.message || '密码修改失败';
                }
            } catch (e) {
                changePasswordError.value = e.message || '密码修改失败，请重试';
            } finally {
                changePasswordLoading.value = false;
            }
        }

        function openChangePasswordModal() {
            changePasswordForm.oldPassword = '';
            changePasswordForm.newPassword = '';
            changePasswordForm.confirmPassword = '';
            changePasswordError.value = '';
            showChangePasswordModal.value = true;
        }

        onMounted(async () => {
            await checkAuth();
            if (isLoggedIn.value) {
                await loadUserMenus();
                loadAgents();
                loadSkills();
                loadAllPermissions();
                loadPermissionUsers();
                loadPermissionRoles();
                loadDepartments();
            }
        });

        // ========================================
        // return
        // ========================================
        return {
            // 登录状态
            isLoggedIn, currentUser, token, loginForm, loginLoading, loginError,
            // 修改密码
            showChangePasswordModal, changePasswordForm, changePasswordLoading, changePasswordError,
            // 用户菜单
            userMenuOpen,
            // 状态
            currentPage, toasts, sidebarOpen, pageTitle,
            agents, skills, executions,
            selectedAgent, agentSearch, filteredAgents,
            showCreateAgentModal, isEditingAgent, showSettingsPanel,
            agentForm, settingsForm,
            settingsSkillDropdown, settingsSkillSearch, settingsToolDropdown, settingsToolSearch,
            settingsPromptDropdown, settingsPromptSearch,
            createSkillDropdown, createSkillSearch, createPromptDropdown, createPromptSearch,
            availableTools, availableModels, availablePrompts, createToolDropdown, createToolSearch, filteredCreateTools,
            filteredSettingsPrompts, filteredCreatePrompts,
            skillSearch, filteredSkills,
            filteredSettingsSkills, filteredSettingsTools, filteredCreateSkills,
            showCreateSkillModal, showEditSkillModal, creatingSkill, skillForm, editSkillForm,
            chatMessages, renderedChatMessages, chatInput, chatLoading, currentConversationId, uploadedFiles, isUploading,
            showExecutionResultModal, currentExecution,
            permissionTab, dashboardStats,
            // 仪表盘数据
            dashboardData, dashboardActivities, dashboardLoading,
            pieChartRef, lineChartRef,
            popularData, dailyStats, currentDate, systemUptime, chatTrendData,
            // 分页
            agentPage, agentPageSize, agentTotal, agentTotalPages,
            skillPage, skillPageSize, skillTotal, skillTotalPages,
            // MCP管理
            mcpServers, mcpPage, mcpPageSize, mcpTotal, mcpTotalPages, showMcpModal, isEditingMcp, mcpForm, syncingMcpId,
            selectedMcpId, mcpTools, showToolDebugModal, debugTool, debugToolResult, invokingTool,
            hasToolParameters, getToolParamKeys,
            // 模型管理
            models, modelPage, modelPageSize, modelTotal, modelTotalPages, showModelModal, isEditingModel, modelForm, testingModelId,
            // 权限管控
            permissionUsers, permissionRoles, allPermissions,
            departments, departmentTree,
            showUserModal, isEditingUser, userForm,
            showRoleModal, isEditingRole, roleForm,
            showDepartmentModal, isEditingDepartment, departmentForm,
            // 用户菜单
            userMenus,
            // 登录方法
            handleLogin, handleLogout, handleChangePassword, openChangePasswordModal,
            // 方法
            switchPage, showToast, formatDate,
            loadAgents, selectAgent, openCreateAgentModal, openEditAgentModal, closeCreateAgentModal, handleOverlayClick,
            saveAgent, openSettings, saveSettings, startNewConversation, deleteAgent, exportAgent, importAgent,
            toggleAgentSkill, toggleSettingsSkill, toggleSettingsTool, toggleAgentTool, loadAvailableTools, loadAvailableModels, loadAvailablePrompts,
            selectSettingsPrompt, selectCreatePrompt, clearSettingsPrompt, clearCreatePrompt,
            loadSkills, openCreateSkillModal, saveSkill,
            openEditSkillModal, saveEditSkill, deleteSkill, exportSkill, importSkills,
            sendMessage, stopChat, onChatKeydown, triggerFileUpload, handleFileUpload, removeUploadedFile,
            viewExecution, getAgentName, getSkillName, getToolName, renderMarkdown,
            // 仪表盘方法
            loadDashboard, getActivityIcon, formatTime,
            calculateRate, getPieSlice, calculateResourcePercent,
            getMaxChatValue, getChatLinePath, getChatAreaPath,
            getMaxMessageCount, getMaxAgentCount,
            initCharts, updatePieChart, updateLineChart, resizeCharts,
            // 分页方法
            changeAgentPage, changeAgentPageSize,
            changeSkillPage, changeSkillPageSize,
            getAgentPageRange, getSkillPageRange,
            // MCP方法
            loadMcps, openAddMcpModal, openEditMcpModal, saveMcpServer, deleteMcpServer, getMcpStatusIcon, toggleMcpStatus, syncMcpTools,
            selectMcpServer, loadMcpTools, openToolDebugModal, closeToolDebugModal, invokeTool,
            changeMcpPage, changeMcpPageSize,
            // 模型方法
            openAddModelModal, openEditModelModal, saveModel, deleteModel, changeModelPage, changeModelPageSize, testModelConnection,
            // 权限方法
            loadPermissionUsers, loadPermissionRoles, loadAllPermissions, loadUserMenus,
            openAddUserModal, openEditUserModal, saveUser, deleteUser,
            openAddRoleModal, openEditRoleModal, saveRole, deleteRole,
            toggleRolePermission, getPermissionLabel,
            showPermissionModal, isEditingPermission, permissionForm,
            openAddPermissionModal, openEditPermissionModal, savePermission, deletePermission,
            // 部门方法
            loadDepartments, openAddDepartmentModal, openEditDepartmentModal, saveDepartment, deleteDepartment, getDepartmentName,
            initDefaultPermissions,
            // 提示词管理
            prompts, promptPage, promptPageSize, promptTotal, promptTotalPages,
            promptSearch,
            showCreatePromptModal, isEditingPrompt, creatingPrompt, promptForm,
            loadPrompts, openCreatePromptModal, openEditPromptModal, savePrompt, deletePrompt,
            changePromptPage, changePromptPageSize, getPromptPageRange,
            // 知识库管理
            knowledgeBases, kbPage, kbPageSize, kbTotal, kbTotalPages, kbSearch,
            showKbModal, isEditingKb, kbForm,
            kbDocuments, showKbDocModal, kbDocForm,
            loadKnowledgeBases, openAddKbModal, openEditKbModal, saveKnowledgeBase, deleteKnowledgeBase,
            openKbDocModal, saveKbDoc, deleteKbDoc, loadKbDocuments,
            changeKbPage, changeKbPageSize,
            // 知识库详情
            showKbDetailModal, currentKb, kbDetailTab, kbUploadFiles, kbTestQuery, kbTestResults, kbTestLoading,
            openKbDetailModal, handleKbFileSelect, removeKbUploadFile, uploadKbFiles, testKbRetrieval, formatFileSize,
        };
    },

    template: `
    <div>
      <!-- 登录页面 -->
      <div v-if="!isLoggedIn" class="login-container">
        <div class="login-box">
          <div class="login-header">
            <svg class="icon icon-xl"><use href="#icon-robot"/></svg>
            <h1>Skill Agent</h1>
            <p>智能体管理平台</p>
          </div>
          <form class="login-form" @submit.prevent="handleLogin">
            <div class="form-group">
              <label>用户名</label>
              <input type="text" class="form-input" v-model="loginForm.username" placeholder="请输入用户名" required>
            </div>
            <div class="form-group">
              <label>密码</label>
              <input type="password" class="form-input" v-model="loginForm.password" placeholder="请输入密码" required>
            </div>
            <div class="form-error" v-if="loginError">{{ loginError }}</div>
            <button type="submit" class="btn btn-primary btn-block" :disabled="loginLoading">
              <span v-if="!loginLoading">登录</span>
              <svg v-else class="icon icon-spinner spinning"><use href="#icon-spinner"/></svg>
            </button>
          </form>

        </div>
      </div>

      <!-- 主应用 -->
      <template v-else>
      <!-- SVG 图标 -->
      <svg style="display:none">
        <defs>
          <symbol id="icon-robot" viewBox="0 0 24 24"><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.387-1 1.732V7h1a7 7 0 0 1 7 7v4a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3v-4a7 7 0 0 1 7-7h1V5.732A2.001 2.001 0 0 1 12 2zm-4 12a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm8 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2z"/></symbol>
          <symbol id="icon-users" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></symbol>
          <symbol id="icon-cogs" viewBox="0 0 24 24"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L3.16 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.58 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></symbol>
          <symbol id="icon-play-circle" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/></symbol>
          <symbol id="icon-menu" viewBox="0 0 24 24"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></symbol>
          <symbol id="icon-search" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></symbol>
          <symbol id="icon-bell" viewBox="0 0 24 24"><path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></symbol>
          <symbol id="icon-chevron-down" viewBox="0 0 24 24"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/></symbol>
          <symbol id="icon-plus" viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></symbol>
          <symbol id="icon-edit" viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></symbol>
          <symbol id="icon-trash" viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></symbol>
          <symbol id="icon-eye" viewBox="0 0 24 24"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></symbol>
          <symbol id="icon-close" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></symbol>
          <symbol id="icon-redo" viewBox="0 0 24 24"><path d="M12.48 3L7.73 7.75 9.14 9.16 11.1 7.2v.8c0 3.53 2.61 6.43 6 6.92V21h2v-6.08c3.39-.49 6-3.39 6-6.92 0-3.87-3.13-7-7-7-1.21 0-2.35.31-3.35.86l.69-1.13z"/></symbol>
          <symbol id="icon-play" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></symbol>
          <symbol id="icon-check-circle" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></symbol>
          <symbol id="icon-times-circle" viewBox="0 0 24 24"><path d="M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm5 13.59L15.59 17 12 13.41 8.41 17 7 15.59 10.59 12 7 8.41 8.41 7 12 10.59 15.59 7 17 8.41 13.41 12 17 15.59z"/></symbol>
          <symbol id="icon-info-circle" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></symbol>
          <symbol id="icon-exclamation-triangle" viewBox="0 0 24 24"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></symbol>
          <symbol id="icon-dashboard" viewBox="0 0 24 24"><path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/></symbol>
          <symbol id="icon-server" viewBox="0 0 24 24"><path d="M20 13H4c-.55 0-1 .45-1 1v6c0 .55.45 1 1 1h16c.55 0 1-.45 1-1v-6c0-.55-.45-1-1-1zM7 19c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zM20 3H4c-.55 0-1 .45-1 1v6c0 .55.45 1 1 1h16c.55 0 1-.45 1-1V4c0-.55-.45-1-1-1zM7 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/></symbol>
          <symbol id="icon-cpu" viewBox="0 0 24 24"><path d="M15 1H9v2H7v2H5v2H3v2H1v2h2v2h2v2h2v2h2v2h6v-2h2v-2h2v-2h2v-2h2v-2h-2V7h-2V5h-2V3h-2V1zm-3 6c2.21 0 4 1.79 4 4s-1.79 4-4 4-4-1.79-4-4 1.79-4 4-4z"/></symbol>
          <symbol id="icon-api" viewBox="0 0 24 24"><path d="M14 12l-2 2-2-2 2-2 2 2zm-2-6l2.12 2.12 2.5-2.5L12 1 7.38 5.62l2.5 2.5L12 6zm-6 6l2.12-2.12-2.5-2.5L1 12l4.62 4.62 2.5-2.5L6 12zm12 0l-2.12 2.12 2.5 2.5L23 12l-4.62-4.62-2.5 2.5L18 12zm-6 6l-2.12-2.12-2.5 2.5L12 23l4.62-4.62-2.5-2.5L12 18z"/></symbol>
          <symbol id="icon-database" viewBox="0 0 24 24"><path d="M12 3C7.58 3 4 4.79 4 7v10c0 2.21 3.58 4 8 4s8-1.79 8-4V7c0-2.21-3.58-4-8-4zm0 2c3.87 0 6 1.5 6 2s-2.13 2-6 2-6-1.5-6-2 2.13-2 6-2zm6 12c0 .5-2.13 2-6 2s-6-1.5-6-2v-2.23c1.61.78 3.72 1.23 6 1.23s4.39-.45 6-1.23V17zm0-5c0 .5-2.13 2-6 2s-6-1.5-6-2V9.77c1.61.78 3.72 1.23 6 1.23s4.39-.45 6-1.23V12z"/></symbol>
          <symbol id="icon-shield" viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/></symbol>
          <symbol id="icon-inbox" viewBox="0 0 24 24"><path d="M19 3H4.99c-1.11 0-1.98.89-1.98 2L3 19c0 1.1.88 2 1.99 2H19c1.1 0 2-.9 2-2V5c0-1.11-.9-2-2-2zm0 12h-4c0 1.66-1.35 3-3 3s-3-1.34-3-3H4.99V5H19v10z"/></symbol>
          <symbol id="icon-upload" viewBox="0 0 24 24"><path d="M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z"/></symbol>
          <symbol id="icon-download" viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></symbol>
          <symbol id="icon-logout" viewBox="0 0 24 24"><path d="M10.09 15.59L11.5 17l5-5-5-5-1.41 1.41L12.67 11H3v2h9.67l-2.58 2.59zM19 3H5c-1.11 0-2 .9-2 2v4h2V5h14v14H5v-4H3v4c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"/></symbol>
          <symbol id="icon-spinner" viewBox="0 0 24 24"><path d="M12 6v3l4-4-4-4v3c-4.42 0-8 3.58-8 8 0 1.57.46 3.03 1.24 4.26L6.7 14.8c-.45-.83-.7-1.79-.7-2.8 0-3.31 2.69-6 6-6zm6.76 1.74L17.3 9.2c.44.84.7 1.79.7 2.8 0 3.31-2.69 6-6 6v-3l-4 4 4 4v-3c4.42 0 8-3.58 8-8 0-1.57-.46-3.03-1.24-4.26z"/></symbol>
          <symbol id="icon-key" viewBox="0 0 24 24"><path d="M12.65 10C11.83 7.67 9.61 6 7 6c-3.31 0-6 2.69-6 6s2.69 6 6 6c2.61 0 4.83-1.67 5.65-4H17v4h4v-4h2v-4H12.65zM7 14c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/></symbol>
          <symbol id="icon-boomerang" viewBox="0 0 24 24"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></symbol>
        </defs>
      </svg>

      <div class="app-container">
        <!-- 侧边栏 -->
        <aside class="sidebar" :class="{ open: sidebarOpen }">
          <div class="logo">
            <svg class="icon icon-xl"><use href="#icon-robot"/></svg>
            <span>Skill Agent</span>
          </div>
          <nav class="nav-menu">
            <a v-for="menu in userMenus" :key="menu.id" href="#" class="nav-item" :class="{ active: currentPage===menu.path }" @click.prevent="switchPage(menu.path)">
              <svg class="icon icon-lg"><use :href="'#icon-' + (menu.icon || 'circle')"/></svg><span>{{ menu.name }}</span>
            </a>
          </nav>
        </aside>

        <!-- 主内容区 -->
        <main class="main-content">
          <!-- 顶部栏 -->
          <header class="header">
            <div class="header-left">
              <button class="menu-toggle" @click="sidebarOpen = !sidebarOpen">
                <svg class="icon icon-lg"><use href="#icon-menu"/></svg>
              </button>
              <h1 class="page-title">{{ pageTitle }}</h1>
            </div>
            <div class="header-right">
              <div class="user-menu" v-click-outside="() => userMenuOpen = false">
                <div class="user-profile" @click="userMenuOpen = !userMenuOpen">
                  <div class="avatar" style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;display:flex;align-items:center;justify-content:center;font-weight:600;">{{ currentUser?.username?.charAt(0)?.toUpperCase() || '管' }}</div>
                  <span>{{ currentUser?.username || '管理员' }}</span>
                  <svg class="icon" :class="{ 'rotate-180': userMenuOpen }"><use href="#icon-chevron-down"/></svg>
                </div>
                <div class="user-dropdown" v-show="userMenuOpen">
                  <div class="user-dropdown-item" @click="openChangePasswordModal">
                    <svg class="icon"><use href="#icon-key"/></svg>
                    <span>修改密码</span>
                  </div>
                  <div class="user-dropdown-divider"></div>
                  <div class="user-dropdown-item" @click="handleLogout">
                    <svg class="icon"><use href="#icon-logout"/></svg>
                    <span>退出登录</span>
                  </div>
                </div>
              </div>
            </div>
          </header>

          <!-- 仪表盘 -->
          <div v-if="currentPage==='dashboard'" class="page-content">
            <div class="dashboard-wrapper">
              <!-- 核心指标卡片区 -->
              <div class="metrics-section">
                <div class="metrics-grid">
                  <div class="metric-card primary" @click="switchPage('agents')">
                    <div class="metric-icon">
                      <svg class="icon"><use href="#icon-users"/></svg>
                    </div>
                    <div class="metric-content">
                      <div class="metric-value">{{ dashboardData.agents.total }}</div>
                      <div class="metric-label">智能体</div>
                      <div class="metric-sub">{{ dashboardData.agents.active }} 活跃</div>
                    </div>
                    <div class="metric-trend up" v-if="dashboardData.agents.today_count > 0">+{{ dashboardData.agents.today_count }}</div>
                  </div>

                  <div class="metric-card success" @click="switchPage('skills')">
                    <div class="metric-icon">
                      <svg class="icon"><use href="#icon-cogs"/></svg>
                    </div>
                    <div class="metric-content">
                      <div class="metric-value">{{ dashboardData.skills.total }}</div>
                      <div class="metric-label">技能</div>
                      <div class="metric-sub">今日 +{{ dashboardData.skills.today_count }}</div>
                    </div>
                    <div class="metric-trend up" v-if="dashboardData.skills.today_count > 0">+{{ dashboardData.skills.today_count }}</div>
                  </div>

                  <div class="metric-card info" @click="switchPage('mcp')">
                    <div class="metric-icon">
                      <svg class="icon"><use href="#icon-server"/></svg>
                    </div>
                    <div class="metric-content">
                      <div class="metric-value">{{ dashboardData.mcps.active }}</div>
                      <div class="metric-label">MCP服务</div>
                      <div class="metric-sub">{{ dashboardData.mcps.active === dashboardData.mcps.total ? '全部运行' : '部分运行' }}</div>
                    </div>
                    <div class="metric-trend" :class="dashboardData.mcps.active === dashboardData.mcps.total ? 'up' : 'down'">{{ dashboardData.mcps.active }}/{{ dashboardData.mcps.total }}</div>
                  </div>

                  <div class="metric-card warning" @click="switchPage('permission')">
                    <div class="metric-icon">
                      <svg class="icon"><use href="#icon-user"/></svg>
                    </div>
                    <div class="metric-content">
                      <div class="metric-value">{{ dashboardData.users.active }}</div>
                      <div class="metric-label">在线用户</div>
                      <div class="metric-sub">共 {{ dashboardData.users.total }} 用户</div>
                    </div>
                    <div class="metric-trend up" v-if="dashboardData.users.today_count > 0">+{{ dashboardData.users.today_count }}</div>
                  </div>
                </div>
              </div>

              <!-- 图表区域 -->
              <div class="charts-section">
                <div class="charts-grid">
                  <!-- 资源分布饼图 -->
                  <div class="chart-card">
                    <div class="chart-header">
                      <h4>资源分布</h4>
                    </div>
                    <div ref="pieChartRef" class="echart-container"></div>
                  </div>

                  <!-- 对话趋势折线图 -->
                  <div class="chart-card wide">
                    <div class="chart-header">
                      <h4>对话趋势</h4>
                    </div>
                    <div ref="lineChartRef" class="echart-container"></div>
                  </div>
                </div>
              </div>

              <!-- 热门排行榜 -->
              <div class="popular-section">
                <div class="section-title">
                  <svg class="icon"><use href="#icon-trophy"/></svg>
                  <h3>热门排行榜</h3>
                </div>
                <div class="popular-grid">
                  <!-- 热门智能体 -->
                  <div class="popular-card">
                    <div class="popular-header">
                      <svg class="icon"><use href="#icon-users"/></svg>
                      <h4>热门智能体</h4>
                      <span class="popular-subtitle">按对话次数</span>
                    </div>
                    <div class="popular-list">
                      <template v-if="popularData && popularData.popular_agents && popularData.popular_agents.length">
                        <div v-for="(agent, index) in popularData.popular_agents" :key="agent.agent_id" class="popular-item">
                          <div class="popular-rank" :class="'rank-' + (index + 1)">{{ index + 1 }}</div>
                          <div class="popular-info">
                            <div class="popular-name">{{ agent.name }}</div>
                            <div class="popular-bar">
                              <div class="popular-progress" :style="{ width: calculateRate(agent.message_count, getMaxMessageCount()) + '%' }"></div>
                            </div>
                          </div>
                          <div class="popular-count">{{ agent.message_count }}</div>
                        </div>
                      </template>
                      <div v-else class="popular-empty">暂无数据 ({{ popularData ? popularData.popular_agents?.length : 'no data' }})</div>
                    </div>
                  </div>

                  <!-- 热门技能 -->
                  <div class="popular-card">
                    <div class="popular-header">
                      <svg class="icon"><use href="#icon-cogs"/></svg>
                      <h4>热门技能</h4>
                      <span class="popular-subtitle">按绑定Agent数</span>
                    </div>
                    <div class="popular-list">
                      <template v-if="popularData && popularData.popular_skills && popularData.popular_skills.length">
                        <div v-for="(skill, index) in popularData.popular_skills" :key="skill.skill_id" class="popular-item">
                          <div class="popular-rank" :class="'rank-' + (index + 1)">{{ index + 1 }}</div>
                          <div class="popular-info">
                            <div class="popular-name">{{ skill.name }}</div>
                            <div class="popular-bar">
                              <div class="popular-progress skill" :style="{ width: calculateRate(skill.agent_count, getMaxAgentCount()) + '%' }"></div>
                            </div>
                          </div>
                          <div class="popular-count">{{ skill.agent_count }}</div>
                        </div>
                      </template>
                      <div v-else class="popular-empty">暂无数据 ({{ popularData ? popularData.popular_skills?.length : 'no data' }})</div>
                    </div>
                  </div>

                  <!-- 热门MCP -->
                  <div class="popular-card">
                    <div class="popular-header">
                      <svg class="icon"><use href="#icon-server"/></svg>
                      <h4>热门MCP</h4>
                      <span class="popular-subtitle">最近使用</span>
                    </div>
                    <div class="popular-list">
                      <template v-if="popularData.popular_mcps && popularData.popular_mcps.length">
                        <div v-for="(mcp, index) in popularData.popular_mcps" :key="mcp.mcp_id" class="popular-item">
                          <div class="popular-rank" :class="'rank-' + (index + 1)">{{ index + 1 }}</div>
                          <div class="popular-info">
                            <div class="popular-name">{{ mcp.name }}</div>
                            <div class="popular-meta">{{ formatTime(mcp.created_at) }}</div>
                          </div>
                        </div>
                      </template>
                      <div v-else class="popular-empty">暂无数据</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 底部两栏：最近活动 + 快捷入口 -->
              <div class="dashboard-bottom">
                <div class="dashboard-section activities">
                  <div class="section-header">
                    <h3>
                      <svg class="icon"><use href="#icon-clock"/></svg>
                      最近活动
                    </h3>
                    <a href="#" class="view-all" @click.prevent="switchPage('agents')">查看全部</a>
                  </div>
                  <div class="activity-timeline" v-if="dashboardActivities.length > 0">
                    <div v-for="(activity, index) in dashboardActivities.slice(0, 5)" :key="activity.id" class="timeline-item">
                      <div class="timeline-dot" :class="activity.activity_type"></div>
                      <div class="timeline-content">
                        <div class="timeline-title">{{ activity.title }}</div>
                        <div class="timeline-desc">{{ activity.description }}</div>
                        <div class="timeline-meta">
                          <span class="timeline-user">
                            <svg class="icon"><use href="#icon-user"/></svg>
                            {{ activity.user_name }}
                          </span>
                          <span class="timeline-time">{{ formatTime(activity.created_at) }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="empty-state" v-else>
                    <svg class="icon icon-xl"><use href="#icon-inbox"/></svg>
                    <p>暂无活动记录</p>
                  </div>
                </div>

                <div class="dashboard-section quick-links">
                  <div class="section-header">
                    <h3>
                      <svg class="icon"><use href="#icon-plus"/></svg>
                      快捷入口
                    </h3>
                  </div>
                  <div class="quick-links-grid">
                    <div class="quick-link" @click.stop="switchPage('agents'); openCreateAgentModal()">
                      <div class="quick-link-icon primary">
                        <svg class="icon"><use href="#icon-users"/></svg>
                      </div>
                      <span>创建智能体</span>
                    </div>
                    <div class="quick-link" @click.stop="switchPage('skills'); openCreateSkillModal()">
                      <div class="quick-link-icon success">
                        <svg class="icon"><use href="#icon-cogs"/></svg>
                      </div>
                      <span>创建技能</span>
                    </div>
                    <div class="quick-link" @click="switchPage('mcp'); openAddMcpModal()">
                      <div class="quick-link-icon info">
                        <svg class="icon"><use href="#icon-server"/></svg>
                      </div>
                      <span>添加MCP</span>
                    </div>
                    <div class="quick-link" @click="switchPage('permission'); openAddUserModal()">
                      <div class="quick-link-icon warning">
                        <svg class="icon"><use href="#icon-user"/></svg>
                      </div>
                      <span>添加用户</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Agent管理 -->
          <div v-if="currentPage==='agents'" class="page-content" style="display:flex">
            <div class="content-wrapper">
              <!-- 左侧Agent列表 -->
              <div class="agent-list-panel">
                <div class="panel-header">
                  <h2>智能体列表</h2>
                  <div class="header-actions">
                    <button class="btn btn-secondary" @click="importAgent">
                      <svg class="icon"><use href="#icon-upload"/></svg> 导入
                    </button>
                    <button class="btn btn-primary" id="create-agent-btn" @click.stop="openCreateAgentModal">
                      <svg class="icon"><use href="#icon-plus"/></svg> 创建
                    </button>
                  </div>
                </div>
                <div class="panel-body">
                  <div class="search-input">
                    <svg class="icon"><use href="#icon-search"/></svg>
                    <input type="text" placeholder="搜索Agent..." v-model="agentSearch" @input="loadAgents">
                  </div>
                  <div class="agent-list">
                    <div v-if="agents.length===0" class="empty-state">
                      <svg class="icon icon-xl"><use href="#icon-users"/></svg>
                      <h3>暂无智能体</h3>
                      <p>点击"创建"按钮添加智能体</p>
                    </div>
                    <div v-for="agent in agents" :key="agent.id"
                         class="agent-item" :class="{ active: selectedAgent && selectedAgent.id===agent.id }"
                         @click="selectAgent(agent)">
                      <div class="agent-info">
                        <div class="agent-name">{{ agent.name }}</div>
                        <div class="agent-desc">{{ agent.description || '暂无描述' }}</div>
                      </div>
                    </div>
                    <!-- 分页 -->
                    <div class="pagination" v-if="agentTotalPages > 1">
                      <div class="pagination-info">共 {{ agentTotal }} 条，{{ agentTotalPages }} 页</div>
                      <div class="pagination-controls">
                        <button class="btn btn-small" :disabled="agentPage<=1" @click="changeAgentPage(agentPage-1)">上一页</button>
                        <button v-for="p in getAgentPageRange()" :key="p"
                                class="btn btn-small" :class="{ active: p===agentPage }"
                                @click="changeAgentPage(p)">{{ p }}</button>
                        <button class="btn btn-small" :disabled="agentPage>=agentTotalPages" @click="changeAgentPage(agentPage+1)">下一页</button>
                      </div>
                      <div class="pagination-size">
                        <select v-model="agentPageSize" @change="changeAgentPageSize(agentPageSize)">
                          <option :value="10">10条/页</option>
                          <option :value="20">20条/页</option>
                          <option :value="50">50条/页</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 右侧对话/设置区 -->
              <div class="agent-dialog-panel">
                <!-- 聊天模式 header -->
                <div class="panel-header">
                  <h2>{{ selectedAgent ? selectedAgent.name : '选择智能体' }}</h2>
                  <div class="header-actions" v-if="selectedAgent">
                    <button class="btn btn-icon btn-new-chat" @click="startNewConversation" title="新会话" style="display: flex !important; align-items: center !important; justify-content: center !important; width: 36px !important; height: 36px !important; border: 1px solid #e5e7eb !important; background: #fff !important; color: #6b7280 !important; border-radius: 6px !important; padding: 0 !important;">
                      <svg style="width: 18px !important; height: 18px !important; fill: currentColor !important; display: block !important;" viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                    </button>
                    <button class="btn btn-secondary" @click="openSettings(selectedAgent)">
                      <svg class="icon"><use href="#icon-cogs"/></svg> 设置
                    </button>
                  </div>
                </div>

                <!-- 设置侧边抽屉 -->
                <div v-if="showSettingsPanel && selectedAgent" class="settings-drawer">
                  <div class="settings-header">
                    <h3>智能体设置</h3>
                    <button class="btn btn-icon" @click="showSettingsPanel=false">
                      <svg class="icon"><use href="#icon-close"/></svg>
                    </button>
                  </div>
                  <div class="settings-body">
                    <div class="settings-section">
                      <h4>基本信息</h4>
                      <div class="form-group">
                        <label>名称</label>
                        <input type="text" class="form-input" v-model="settingsForm.name">
                      </div>
                      <div class="form-group">
                        <label>描述</label>
                        <textarea class="form-textarea" v-model="settingsForm.description"></textarea>
                      </div>
                      <div class="form-group">
                        <label>可见范围</label>
                        <select class="form-input" v-model="settingsForm.agentSpace">
                          <option value="private">私有 (仅自己可见)</option>
                          <option value="group">部门 (同部门可见)</option>
                          <option value="public">公开 (所有人可见)</option>
                        </select>
                        <small class="form-help">{{ settingsForm.agentSpace === 'private' ? '只有您自己可以查看和使用此智能体' : settingsForm.agentSpace === 'group' ? '同部门成员可以查看和使用此智能体' : '所有用户都可以查看和使用此智能体' }}</small>
                      </div>
                      <div class="form-group" v-if="selectedAgent?.created_by === currentUser?.user_id">
                        <label class="checkbox-label">
                          <input type="checkbox" v-model="settingsForm.isLocked">
                          <span>锁定配置</span>
                        </label>
                        <small class="form-help">{{ settingsForm.isLocked ? '开启后，仅创建者可以修改此智能体的配置' : '关闭时，所有有权限的用户都可以修改配置' }}</small>
                      </div>
                      <div class="form-group" v-else-if="selectedAgent?.is_locked">
                        <label class="checkbox-label" style="opacity: 0.6; cursor: not-allowed;">
                          <input type="checkbox" checked disabled>
                          <span>已锁定配置</span>
                        </label>
                        <small class="form-help">仅创建者可以修改此锁定状态</small>
                      </div>
                    </div>
                    <div class="settings-section">
                      <h4>技能配置</h4>
                      <div class="skill-chips" style="margin-bottom:8px" v-if="settingsForm.skillIds.length > 0">
                        <div v-for="id in settingsForm.skillIds" :key="id" class="skill-chip">
                          {{ settingsForm.skillNames[id] || getSkillName(id) }}
                          <span class="skill-chip-remove" @click="toggleSettingsSkill(id)">×</span>
                        </div>
                      </div>
                      <div class="skill-dropdown" v-click-outside="() => settingsSkillDropdown = false">
                        <div class="skill-dropdown-trigger" @click="settingsSkillDropdown = !settingsSkillDropdown">
                          <span>{{ settingsForm.skillIds.length ? '已选 ' + settingsForm.skillIds.length + ' 个技能' : '— 选择技能 —' }}</span>
                          <svg class="icon" style="width:14px;height:14px;transition:transform .2s" :style="settingsSkillDropdown ? 'transform:rotate(180deg)' : ''"><use href="#icon-chevron-down"/></svg>
                        </div>
                        <div class="skill-dropdown-menu" v-if="settingsSkillDropdown">
                          <div class="skill-dropdown-search">
                            <input type="text" placeholder="搜索技能..." v-model="settingsSkillSearch" class="skill-dropdown-input" @click.stop>
                          </div>
                          <div class="skill-dropdown-list">
                            <div v-if="filteredSettingsSkills.length === 0" class="skill-empty">暂无匹配技能</div>
                            <div v-for="skill in filteredSettingsSkills" :key="skill.id"
                                 class="skill-dropdown-item"
                                 :class="{ selected: settingsForm.skillIds.includes(skill.id) }"
                                 @click.stop="toggleSettingsSkill(skill.id)">
                              <span class="skill-dropdown-check">{{ settingsForm.skillIds.includes(skill.id) ? '✓' : '' }}</span>
                              <span>{{ skill.name }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div class="settings-section">
                      <h4>工具配置</h4>
                      <div class="skill-chips" style="margin-bottom:8px" v-if="settingsForm.toolIds.length > 0">
                        <div v-for="id in settingsForm.toolIds" :key="id" class="skill-chip">
                          {{ settingsForm.toolNames[id] || getToolName(id) }}
                          <span class="skill-chip-remove" @click="toggleSettingsTool(id)">×</span>
                        </div>
                      </div>
                      <div class="skill-dropdown" v-click-outside="() => settingsToolDropdown = false">
                        <div class="skill-dropdown-trigger" @click="settingsToolDropdown = !settingsToolDropdown">
                          <span>{{ settingsForm.toolIds.length ? '已选 ' + settingsForm.toolIds.length + ' 个工具' : '— 选择工具 —' }}</span>
                          <svg class="icon" style="width:14px;height:14px;transition:transform .2s" :style="settingsToolDropdown ? 'transform:rotate(180deg)' : ''"><use href="#icon-chevron-down"/></svg>
                        </div>
                        <div class="skill-dropdown-menu" v-if="settingsToolDropdown">
                          <div class="skill-dropdown-search">
                            <input type="text" placeholder="搜索工具..." v-model="settingsToolSearch" class="skill-dropdown-input" @click.stop>
                          </div>
                          <div class="skill-dropdown-list">
                            <div v-if="filteredSettingsTools.length === 0" class="skill-empty">暂无匹配工具</div>
                            <div v-for="tool in filteredSettingsTools" :key="tool.id"
                                 class="skill-dropdown-item"
                                 :class="{ selected: settingsForm.toolIds.includes(tool.id) }"
                                 @click.stop="toggleSettingsTool(tool.id)">
                              <span class="skill-dropdown-check">{{ settingsForm.toolIds.includes(tool.id) ? '✓' : '' }}</span>
                              <span>{{ tool.name }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div class="settings-section">
                      <h4>模型配置</h4>
                      <div class="form-group">
                        <label>选择模型</label>
                        <select class="form-input" v-model="settingsForm.modelId">
                          <option value="">— 请选择模型 —</option>
                          <option v-for="model in availableModels" :key="model.id" :value="model.id">
                            {{ model.name }} ({{ model.model_name }})
                          </option>
                        </select>
                        <small class="form-hint">选择要使用的AI模型，留空将使用默认模型</small>
                      </div>
                      <div class="form-group">
                        <label>提示词</label>
                        <div class="skill-chips" style="margin-bottom:8px" v-if="settingsForm.promptId">
                          <div class="skill-chip">
                            {{ settingsForm.promptName || availablePrompts.find(p => p.id === settingsForm.promptId)?.name || settingsForm.promptId }}
                            <span class="skill-chip-remove" @click="clearSettingsPrompt">×</span>
                          </div>
                        </div>
                        <div class="skill-dropdown" v-click-outside="() => settingsPromptDropdown = false">
                          <div class="skill-dropdown-trigger" @click="settingsPromptDropdown = !settingsPromptDropdown">
                            <span>{{ settingsForm.promptId ? '更换提示词' : '— 选择提示词 —' }}</span>
                            <svg class="icon" style="width:14px;height:14px;transition:transform .2s" :style="settingsPromptDropdown ? 'transform:rotate(180deg)' : ''"><use href="#icon-chevron-down"/></svg>
                          </div>
                          <div class="skill-dropdown-menu" v-if="settingsPromptDropdown">
                            <div class="skill-dropdown-search">
                              <input type="text" placeholder="搜索提示词..." v-model="settingsPromptSearch" class="skill-dropdown-input" @click.stop>
                            </div>
                            <div class="skill-dropdown-list">
                              <div v-if="filteredSettingsPrompts.length === 0" class="skill-empty">暂无匹配提示词</div>
                              <div v-for="prompt in filteredSettingsPrompts" :key="prompt.id"
                                   class="skill-dropdown-item"
                                   :class="{ selected: settingsForm.promptId === prompt.id }"
                                   @click.stop="selectSettingsPrompt(prompt)">
                                <span class="skill-dropdown-check">{{ settingsForm.promptId === prompt.id ? '✓' : '' }}</span>
                                <span>{{ prompt.name }}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                        <small class="form-hint" v-if="settingsForm.promptId">选择提示词后，智能体将使用该提示词作为系统提示</small>
                      </div>
                    </div>
                    <div class="settings-section">
                      <h4>模型参数</h4>
                      <div class="form-group">
                        <label>温度值 (Temperature): {{ settingsForm.temperature }}</label>
                        <input type="range" class="form-range" min="0" max="2" step="0.1" v-model="settingsForm.temperature">
                        <small class="form-hint">控制输出的随机性，值越高输出越多样，值越低输出越确定</small>
                      </div>
                      <div class="form-group">
                        <label>多样性 (Top P): {{ settingsForm.topP }}</label>
                        <input type="range" class="form-range" min="0" max="1" step="0.05" v-model="settingsForm.topP">
                        <small class="form-hint">控制输出的多样性，值越高考虑的词越多，输出越多样</small>
                      </div>
                      <div class="form-group">
                        <label class="checkbox-label">
                          <input type="checkbox" v-model="settingsForm.enableMemory">
                          <span>启用记忆</span>
                        </label>
                        <small class="form-hint">开启后，AI会记住对话历史，提供更连贯的回答</small>
                      </div>
                    </div>
                    <div class="settings-actions">
                      <button class="btn btn-secondary" @click="exportAgent(selectedAgent)">
                        <svg class="icon"><use href="#icon-download"/></svg> 导出
                      </button>
                      <button class="btn btn-danger" @click="deleteAgent(selectedAgent.id)">删除</button>
                      <button class="btn btn-secondary" @click="showSettingsPanel=false">取消</button>
                      <button class="btn btn-primary" @click="saveSettings">保存</button>
                    </div>
                  </div>
                </div>

                <!-- 聊天区域 -->
                <template v-if="true">
                  <div v-if="!selectedAgent" class="chat-container" style="display:flex;align-items:center;justify-content:center">
                    <div class="empty-state">
                      <svg class="icon icon-xl"><use href="#icon-robot"/></svg>
                      <h3>请从左侧选择智能体</h3>
                      <p>选择一个智能体后，您可以开始与它对话</p>
                    </div>
                  </div>
                  <div v-else id="chatMessages" class="chat-container" style="overflow-y:auto;flex:1;padding:16px">
                    <div v-for="(msg, idx) in renderedChatMessages" :key="idx"
                         class="message" :class="msg.role">
                      <div v-if="msg.role === 'user'" class="message-content">{{ msg.content }}</div>
                      <div v-else class="message-content" v-html="msg.renderedContent"></div>
                      <div class="message-time" v-if="msg.time">{{ msg.time }}</div>
                    </div>
                    <div v-if="chatLoading" class="message agent loading">
                      <div class="message-content">
                        <div class="spinner"></div>
                        <span>正在思考...</span>
                      </div>
                    </div>
                  </div>
                  <div class="chat-input-area" v-if="selectedAgent">
                    <!-- 文件上传按钮 -->
                    <input type="file" id="fileInput" style="display: none" @change="handleFileUpload" multiple>
                    <button class="btn btn-secondary" @click="triggerFileUpload" :disabled="isUploading || chatLoading" title="上传文件">
                      <svg class="icon" v-if="!isUploading"><use href="#icon-upload"/></svg>
                      <span v-else class="spinner-small"></span>
                    </button>
                    <input type="text" class="chat-input" placeholder="输入消息..."
                           v-model="chatInput" @keydown="onChatKeydown" :disabled="chatLoading">
                    <!-- 发送按钮 / 终止按钮 -->
                    <button v-if="!chatLoading" class="btn btn-primary" @click="sendMessage">
                      <svg class="icon"><use href="#icon-play"/></svg>
                    </button>
                    <button v-else class="btn btn-danger" @click="stopChat" title="终止对话">
                      <svg class="icon"><use href="#icon-stop"/></svg>
                    </button>
                  </div>
                  <!-- 已上传文件列表 -->
                  <div class="uploaded-files" v-if="uploadedFiles.length > 0 && selectedAgent">
                    <div class="file-tag" v-for="(file, idx) in uploadedFiles" :key="idx">
                      <svg class="icon"><use href="#icon-file"/></svg>
                      <span class="file-name">{{ file.name }}</span>
                      <button class="file-remove" @click="removeUploadedFile(idx)">×</button>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <!-- Skill管理 -->
          <div v-if="currentPage==='skills'" class="page-content" style="display:flex">
            <div class="content-container">
              <div class="page-header">
                <h2>Skill管理</h2>
                <div class="header-actions">
                  <div class="search-input">
                    <svg class="icon"><use href="#icon-search"/></svg>
                    <input type="text" placeholder="搜索Skill..." v-model="skillSearch" @input="loadSkills">
                  </div>
                  <button class="btn btn-primary" @click="openCreateSkillModal">
                    <svg class="icon"><use href="#icon-plus"/></svg> 创建Skill
                  </button>
                  <button class="btn btn-secondary" @click="importSkills">
                    <svg class="icon"><use href="#icon-upload"/></svg> 导入Skills
                  </button>
                </div>
              </div>
              <div class="skill-list skill-list-vertical">
                <div v-if="skills.length===0" class="empty-state">
                  <svg class="icon icon-xl"><use href="#icon-cogs"/></svg>
                  <h3>暂无Skill</h3><p>点击"创建Skill"按钮添加技能</p>
                </div>
                <div v-for="skill in skills" :key="skill.id" class="skill-card">
                  <div class="skill-card-header">
                    <h3>{{ skill.name }}</h3>
                    <div class="skill-actions">
                      <button class="btn btn-icon btn-edit" @click="openEditSkillModal(skill.id)" title="编辑"><svg class="icon" viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg></button>
                      <button class="btn btn-icon btn-export" @click="exportSkill(skill)" title="下载"><svg class="icon" viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg></button>
                      <button class="btn btn-icon btn-danger" @click="deleteSkill(skill.id)" title="删除"><svg class="icon" viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg></button>
                    </div>
                  </div>
                  <p class="skill-desc">{{ skill.description || '暂无描述' }}</p>
                </div>
                <!-- 分页 -->
                <div class="pagination" v-if="skillTotalPages > 1">
                  <div class="pagination-info">共 {{ skillTotal }} 条，{{ skillTotalPages }} 页</div>
                  <div class="pagination-controls">
                    <button class="btn btn-small" :disabled="skillPage<=1" @click="changeSkillPage(skillPage-1)">上一页</button>
                    <button v-for="p in getSkillPageRange()" :key="p"
                            class="btn btn-small" :class="{ active: p===skillPage }"
                            @click="changeSkillPage(p)">{{ p }}</button>
                    <button class="btn btn-small" :disabled="skillPage>=skillTotalPages" @click="changeSkillPage(skillPage+1)">下一页</button>
                  </div>
                  <div class="pagination-size">
                    <select v-model="skillPageSize" @change="changeSkillPageSize(skillPageSize)">
                      <option :value="10">10条/页</option>
                      <option :value="20">20条/页</option>
                      <option :value="50">50条/页</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 提示词管理 -->
          <div v-if="currentPage==='prompts'" class="page-content" style="display:flex">
            <div class="content-container">
              <div class="page-header">
                <h2>提示词管理</h2>
                <div class="header-actions">
                  <div class="search-input">
                    <svg class="icon"><use href="#icon-search"/></svg>
                    <input type="text" placeholder="搜索提示词..." v-model="promptSearch" @input="loadPrompts">
                  </div>
                  <button class="btn btn-primary" @click="openCreatePromptModal">
                    <svg class="icon"><use href="#icon-plus"/></svg> 创建提示词
                  </button>
                </div>
              </div>
              <div class="prompt-list">
                <div v-if="prompts.length===0" class="empty-state">
                  <svg class="icon icon-xl"><use href="#icon-file-text"/></svg>
                  <h3>暂无提示词</h3><p>点击"创建提示词"按钮添加提示词</p>
                </div>
                <div v-for="prompt in prompts" :key="prompt.id" class="prompt-card" :class="{ inactive: !prompt.is_active }">
                  <div class="prompt-card-header">
                    <div class="prompt-title-section">
                      <h3>{{ prompt.name }}</h3>
                      <span class="prompt-type-badge" :class="prompt.type">{{ prompt.type==='public'?'公开':prompt.type==='group'?'组内':'私有' }}</span>
                      <span v-if="!prompt.is_active" class="status-badge inactive">已停用</span>
                    </div>
                    <div class="prompt-actions">
                      <button class="btn btn-icon btn-secondary" @click="openEditPromptModal(prompt.id)" title="编辑">
                        <svg class="icon" viewBox="0 0 24 24" style="width:18px;height:18px;fill:#6b7280;"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
                      </button>
                      <button class="btn btn-icon btn-danger" @click="deletePrompt(prompt.id)" title="删除">
                        <svg class="icon" viewBox="0 0 24 24" style="width:18px;height:18px;fill:white;"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                      </button>
                    </div>
                  </div>
                  <p v-if="prompt.description && prompt.description !== prompt.name" class="prompt-desc">{{ prompt.description }}</p>
                  <div class="prompt-preview">
                    <pre>{{ prompt.content.substring(0, 200) }}{{ prompt.content.length > 200 ? '...' : '' }}</pre>
                  </div>
                </div>
                <!-- 分页 -->
                <div class="pagination" v-if="promptTotalPages > 1">
                  <div class="pagination-info">共 {{ promptTotal }} 条，{{ promptTotalPages }} 页</div>
                  <div class="pagination-controls">
                    <button class="btn btn-small" :disabled="promptPage<=1" @click="changePromptPage(promptPage-1)">上一页</button>
                    <button v-for="p in getPromptPageRange()" :key="p"
                            class="btn btn-small" :class="{ active: p===promptPage }"
                            @click="changePromptPage(p)">{{ p }}</button>
                    <button class="btn btn-small" :disabled="promptPage>=promptTotalPages" @click="changePromptPage(promptPage+1)">下一页</button>
                  </div>
                  <div class="pagination-size">
                    <select v-model="promptPageSize" @change="changePromptPageSize(promptPageSize)">
                      <option :value="10">10条/页</option>
                      <option :value="20">20条/页</option>
                      <option :value="50">50条/页</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- MCP管理 -->
          <div v-if="currentPage==='mcp'" class="page-content" style="display:flex">
            <div class="content-container">
              <div class="page-header"><h2>MCP管理</h2><div class="header-actions"><button class="btn btn-primary" @click="openAddMcpModal"><svg class="icon"><use href="#icon-plus"/></svg> 添加MCP服务</button></div></div>
              <div v-if="mcpServers.length===0" class="empty-state"><svg class="icon icon-xl"><use href="#icon-server"/></svg><h3>暂无MCP服务</h3><p>点击"添加MCP服务"按钮配置MCP服务器</p></div>
              <div v-else class="mcp-list">
                <div v-for="server in mcpServers" :key="server.id" class="mcp-card" :class="{ selected: selectedMcpId === server.id }" @click="selectMcpServer(server.id)">
                  <div class="mcp-card-header">
                    <div class="mcp-card-info">
                      <h3>{{ server.name }}</h3>
                      <span class="mcp-type-badge">{{ {sse:'SSE',stdio:'StdIO','streamable-http':'HTTP Streamable'}[server.type] || server.type }}</span>
                      <span class="mcp-visibility-badge">{{ server.visibility==='public'?'公开':server.visibility==='group'?'组内':'私有' }}</span>
                    </div>
                    <span class="status-badge" :class="server.status">{{ server.status==='active'?'正常':'停止' }}</span>
                  </div>
                  <div class="mcp-card-body">
                    <div class="mcp-detail"><label>端点</label><code>{{ server.endpoint }}</code></div>
                    <div class="mcp-detail" v-if="server.description"><label>描述</label><span>{{ server.description }}</span></div>
                    <div class="mcp-detail"><label>添加时间</label><span>{{ server.createdAt }}</span></div>
                  </div>
                  <div class="mcp-card-actions" @click.stop>
                    <button class="btn btn-sm btn-success" @click="syncMcpTools(server.id)" :disabled="syncingMcpId === server.id">
                      <svg class="icon"><use href="#icon-refresh"/></svg> {{ syncingMcpId === server.id ? '同步中...' : '同步工具' }}
                    </button>
                    <button class="btn btn-sm btn-secondary" @click="toggleMcpStatus(server.id)">
                      <svg class="icon"><use :href="'#'+getMcpStatusIcon(server.status)"/></svg> {{ server.status==='active'?'停止':'启动' }}
                    </button>
                    <button class="btn btn-sm btn-secondary" @click="openEditMcpModal(server.id)"><svg class="icon"><use href="#icon-edit"/></svg> 编辑</button>
                    <button class="btn btn-sm btn-danger" @click="deleteMcpServer(server.id)"><svg class="icon"><use href="#icon-trash"/></svg> 删除</button>
                  </div>
                </div>
              </div>
              <!-- 分页 -->
              <div v-if="mcpTotalPages > 1" class="pagination-container">
                <div class="pagination">
                  <button class="btn btn-sm" :disabled="mcpPage === 1" @click="changeMcpPage(mcpPage - 1)">上一页</button>
                  <span class="page-info">第 {{ mcpPage }} / {{ mcpTotalPages }} 页 (共 {{ mcpTotal }} 条)</span>
                  <button class="btn btn-sm" :disabled="mcpPage === mcpTotalPages" @click="changeMcpPage(mcpPage + 1)">下一页</button>
                </div>
                <div class="page-size-selector">
                  <select v-model="mcpPageSize" @change="changeMcpPageSize(mcpPageSize)">
                    <option :value="10">10条/页</option>
                    <option :value="20">20条/页</option>
                    <option :value="50">50条/页</option>
                  </select>
                </div>
              </div>
            </div>
            <!-- 右侧工具列表面板 -->
            <div class="mcp-tools-panel" v-if="selectedMcpId">
              <div class="panel-header">
                <h3>工具列表</h3>
                <button class="btn btn-icon" @click="selectedMcpId=null">
                  <svg class="icon"><use href="#icon-close"/></svg>
                </button>
              </div>
              <div class="panel-body">
                <div v-if="mcpTools.length===0" class="empty-state">
                  <svg class="icon icon-lg"><use href="#icon-tools"/></svg>
                  <p>暂无工具，请先同步</p>
                </div>
                <div v-else class="tools-list">
                  <div v-for="tool in mcpTools" :key="tool.id" class="tool-item">
                    <div class="tool-header">
                      <span class="tool-name">{{ tool.name }}</span>
                      <button class="btn btn-sm btn-primary" @click="openToolDebugModal(tool)">
                        <svg class="icon"><use href="#icon-play"/></svg> 调试
                      </button>
                    </div>
                    <div class="tool-description" v-if="tool.description">{{ tool.description }}</div>
                    <div class="tool-params" v-if="tool.parameters && tool.parameters.properties">
                      <label>参数:</label>
                      <div class="param-tags">
                        <span v-for="(prop, key) in tool.parameters.properties" :key="key" class="param-tag">{{ key }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 工具调试弹窗 -->
          <div v-if="showToolDebugModal" class="modal active" @click.self="closeToolDebugModal">
            <div class="modal-overlay"></div>
            <div class="modal-container" @click.stop>
              <div class="modal-header">
                <h3>调试工具: {{ debugTool.name }}</h3>
                <button class="btn btn-icon" @click="closeToolDebugModal">
                  <svg class="icon"><use href="#icon-close"/></svg>
                </button>
              </div>
              <div class="modal-body">
                <div class="tool-debug-info" v-if="debugTool.description">
                  <label>描述:</label>
                  <p>{{ debugTool.description }}</p>
                </div>
                <!-- 调试信息 -->
                <div style="background:#f0f0f0;padding:10px;margin:10px 0;font-size:12px;">
                  <p>hasParams: {{ debugTool.parameters ? 'yes' : 'no' }}</p>
                  <p>hasProperties: {{ debugTool.parameters && debugTool.parameters.properties ? 'yes' : 'no' }}</p>
                  <p>keys: {{ debugTool.parameters && debugTool.parameters.properties ? Object.keys(debugTool.parameters.properties).join(',') : 'none' }}</p>
                </div>
                <div v-if="debugTool.parameters && debugTool.parameters.properties && Object.keys(debugTool.parameters.properties).length > 0">
                  <div class="tool-params-form">
                    <label>参数:</label>
                    <div v-for="(prop, key) in debugTool.parameters.properties" :key="key" class="form-group">
                      <label class="param-label">
                        {{ key }}
                        <span v-if="debugTool.parameters.required && debugTool.parameters.required.includes(key)" class="required">*</span>
                        <small v-if="prop.description" class="param-desc">({{ prop.description }})</small>
                      </label>
                      <input
                        type="text"
                        class="form-input"
                        :data-tool-param="key"
                        :placeholder="prop.type || '请输入'"
                      >
                    </div>
                  </div>
                </div>
                <div class="no-params" v-else>
                  <p>此工具无需参数</p>
                </div>
                <div class="tool-result" v-if="debugToolResult !== null">
                  <label>调用结果:</label>
                  <pre class="result-code">{{ JSON.stringify(debugToolResult, null, 2) }}</pre>
                </div>
              </div>
              <div class="modal-footer">
                <button class="btn btn-secondary" @click="closeToolDebugModal">取消</button>
                <button class="btn btn-primary" @click="invokeTool" :disabled="invokingTool">
                  <svg class="icon" :class="{ 'fa-spin': invokingTool }"><use :href="invokingTool ? '#icon-refresh' : '#icon-play'"/></svg>
                  {{ invokingTool ? '调用中...' : '调用工具' }}
                </button>
              </div>
            </div>
          </div>

          <!-- 模型管理 -->
          <div v-if="currentPage==='models'" class="page-content" style="display:flex">
            <div class="content-container">
              <div class="page-header"><h2>模型管理</h2><div class="header-actions"><button class="btn btn-primary" @click="openAddModelModal"><svg class="icon"><use href="#icon-plus"/></svg> 添加模型</button></div></div>
              <div v-if="models.length===0" class="empty-state"><svg class="icon icon-xl"><use href="#icon-cpu"/></svg><h3>暂无模型配置</h3><p>点击"添加模型"按钮配置LLM模型</p></div>
              <div v-else class="model-list">
                <div v-for="mdl in models" :key="mdl.id" class="model-card">
                  <div class="model-card-header">
                    <div class="model-card-info">
                      <h3>{{ mdl.name }}</h3>
                      <span class="model-type-badge" :class="mdl.modelType">{{ mdl.modelType==='chat'?'Chat':mdl.modelType==='embedding'?'Embedding':mdl.modelType==='huggingface'?'HuggingFace':'未知' }}</span>
                      <span class="model-provider-badge">{{ mdl.provider }}</span>
                      <span class="model-status-badge" :class="mdl.status">{{ mdl.status==='active'?'运行中':'已停止' }}</span>
                    </div>
                  </div>
                  <div class="model-card-body">
                    <div class="model-detail"><label>模型ID</label><code>{{ mdl.modelName }}</code></div>
                    <div class="model-detail"><label>接口地址</label><code>{{ mdl.baseUrl || '-' }}</code></div>
                    <div class="model-detail" v-if="mdl.description"><label>描述</label><span>{{ mdl.description }}</span></div>
                    <div class="model-detail"><label>添加时间</label><span>{{ mdl.createdAt }}</span></div>
                  </div>
                  <div class="model-card-actions">
                    <button class="btn btn-sm btn-success" @click="testModelConnection(mdl.id)" :disabled="testingModelId === mdl.id">
                      <svg class="icon"><use href="#icon-play-circle"/></svg> {{ testingModelId === mdl.id ? '测试中...' : '测试连接' }}
                    </button>
                    <button class="btn btn-sm btn-secondary" @click="openEditModelModal(mdl.id)"><svg class="icon"><use href="#icon-edit"/></svg> 编辑</button>
                    <button class="btn btn-sm btn-danger" @click="deleteModel(mdl.id)"><svg class="icon"><use href="#icon-trash"/></svg> 删除</button>
                  </div>
                </div>
              </div>
              <!-- 分页 -->
              <div v-if="modelTotalPages > 1" class="pagination-container">
                <div class="pagination">
                  <button class="btn btn-sm" :disabled="modelPage === 1" @click="changeModelPage(modelPage - 1)">上一页</button>
                  <span class="page-info">第 {{ modelPage }} / {{ modelTotalPages }} 页 (共 {{ modelTotal }} 条)</span>
                  <button class="btn btn-sm" :disabled="modelPage === modelTotalPages" @click="changeModelPage(modelPage + 1)">下一页</button>
                </div>
                <div class="page-size-selector">
                  <select v-model="modelPageSize" @change="changeModelPageSize(modelPageSize)">
                    <option :value="10">10条/页</option>
                    <option :value="20">20条/页</option>
                    <option :value="50">50条/页</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          <!-- 知识库管理 -->
          <div v-if="currentPage==='rag'" class="page-content" style="display:flex">
            <div class="content-container">
              <div class="page-header"><h2>知识库管理</h2><div class="header-actions"><button class="btn btn-primary" @click="openAddKbModal"><svg class="icon"><use href="#icon-plus"/></svg> 创建知识库</button></div></div>
              <div v-if="knowledgeBases.length===0" class="empty-state"><svg class="icon icon-xl"><use href="#icon-database"/></svg><h3>暂无知识库</h3><p>点击"创建知识库"按钮开始构建知识库</p></div>
              <div v-else class="kb-list">
                <div v-for="kb in knowledgeBases" :key="kb.id" class="kb-card" @click="openKbDetailModal(kb)">
                  <div class="kb-card-header">
                    <div class="kb-card-info">
                      <h3>{{ kb.name }}</h3>
                      <span class="kb-type-badge" :class="kb.type">{{ kb.type==='public'?'公开':kb.type==='group'?'部门':'私有' }}</span>
                      <span class="kb-status-badge" :class="kb.status">{{ kb.status==='active'?'启用':'停用' }}</span>
                    </div>
                  </div>
                  <div class="kb-card-body">
                    <div class="kb-detail" v-if="kb.description"><label>描述</label><span>{{ kb.description }}</span></div>
                    <div class="kb-detail" v-if="kb.embedding_model"><label>嵌入模型</label><span>{{ kb.embedding_model }}</span></div>
                    <div class="kb-detail"><label>创建者</label><span>{{ kb.creator_name || '-' }}</span></div>
                    <div class="kb-detail"><label>创建时间</label><span>{{ kb.created_at }}</span></div>
                  </div>
                  <div class="kb-card-actions" @click.stop>
                    <button class="btn btn-sm btn-secondary" @click="openEditKbModal(kb)"><svg class="icon"><use href="#icon-edit"/></svg> 编辑</button>
                    <button class="btn btn-sm btn-danger" @click="deleteKnowledgeBase(kb.id)"><svg class="icon"><use href="#icon-trash"/></svg> 删除</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 权限管控 -->
          <div v-if="currentPage==='permission'" class="page-content" style="display:flex">
            <div class="content-container">
              <div class="page-header"><h2>权限管控</h2></div>
              <div class="permission-tabs">
                <button class="tab-btn" :class="{active:permissionTab==='departments'}" @click="permissionTab='departments'">部门管理</button>
                <button class="tab-btn" :class="{active:permissionTab==='users'}" @click="permissionTab='users'">用户管理</button>
                <button class="tab-btn" :class="{active:permissionTab==='roles'}" @click="permissionTab='roles'">角色管理</button>
                <button class="tab-btn" :class="{active:permissionTab==='permissions'}" @click="permissionTab='permissions'">权限配置</button>
              </div>
              <div class="permission-content">
                <!-- 部门管理 -->
                <div v-if="permissionTab==='departments'" class="tab-content active">
                  <div class="tab-header">
                    <span class="tab-count">共 {{ departments.length }} 个部门</span>
                    <button class="btn btn-primary btn-sm" @click="openAddDepartmentModal">
                      <svg class="icon"><use href="#icon-plus"/></svg> 添加部门
                    </button>
                  </div>
                  <div v-if="departments.length===0" class="empty-state">
                    <svg class="icon icon-xl"><use href="#icon-globe"/></svg>
                    <h3>暂无部门</h3>
                    <p>点击上方按钮添加部门</p>
                  </div>
                  <table v-else class="permission-table">
                    <thead>
                      <tr>
                        <th>部门名称</th>
                        <th>部门编码</th>
                        <th>上级部门</th>
                        <th>状态</th>
                        <th>排序</th>
                        <th>操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="d in departments" :key="d.id">
                        <td><strong>{{ d.name }}</strong></td>
                        <td><code>{{ d.code }}</code></td>
                        <td>{{ getDepartmentName(d.parent_id) }}</td>
                        <td><span class="status-dot" :class="d.status"></span>{{ d.status==='active'?'启用':'停用' }}</td>
                        <td>{{ d.sort_order }}</td>
                        <td class="action-cell">
                          <button class="btn btn-sm btn-secondary" @click="openEditDepartmentModal(d)">
                            <svg class="icon"><use href="#icon-edit"/></svg>
                          </button>
                          <button class="btn btn-sm btn-danger" @click="deleteDepartment(d.id)">
                            <svg class="icon"><use href="#icon-trash"/></svg>
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- 用户管理 -->
                <div v-if="permissionTab==='users'" class="tab-content active">
                  <div class="tab-header">
                    <span class="tab-count">共 {{ permissionUsers.length }} 个用户</span>
                    <button class="btn btn-primary btn-sm" @click="openAddUserModal">
                      <svg class="icon"><use href="#icon-plus"/></svg> 添加用户
                    </button>
                  </div>
                  <div v-if="permissionUsers.length===0" class="empty-state">
                    <svg class="icon icon-xl"><use href="#icon-users"/></svg>
                    <h3>暂无用户</h3>
                  </div>
                  <table v-else class="permission-table">
                    <thead>
                      <tr>
                        <th>用户名</th>
                        <th>姓名</th>
                        <th>邮箱</th>
                        <th>部门</th>
                        <th>角色</th>
                        <th>状态</th>
                        <th>创建时间</th>
                        <th>操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="u in permissionUsers" :key="u.id">
                        <td>{{ u.username }}</td>
                        <td>{{ u.real_name || '-' }}</td>
                        <td>{{ u.email || '-' }}</td>
                        <td>{{ u.department_name || '-' }}</td>
                        <td>
                          <span v-for="role in u.roles" :key="role.id" class="role-tag">{{ role.name }}</span>
                          <span v-if="!u.roles || u.roles.length===0">-</span>
                        </td>
                        <td><span class="status-dot" :class="u.status"></span>{{ u.status==='active'?'启用':'停用' }}</td>
                        <td>{{ u.created_at }}</td>
                        <td class="action-cell">
                          <button class="btn btn-sm btn-secondary" @click="openEditUserModal(u)">
                            <svg class="icon"><use href="#icon-edit"/></svg>
                          </button>
                          <button class="btn btn-sm btn-danger" @click="deleteUser(u.id)">
                            <svg class="icon"><use href="#icon-trash"/></svg>
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- 角色管理 -->
                <div v-if="permissionTab==='roles'" class="tab-content active">
                  <div class="tab-header">
                    <span class="tab-count">共 {{ permissionRoles.length }} 个角色</span>
                    <button class="btn btn-primary btn-sm" @click="openAddRoleModal">
                      <svg class="icon"><use href="#icon-plus"/></svg> 添加角色
                    </button>
                  </div>
                  <div v-if="permissionRoles.length===0" class="empty-state">
                    <svg class="icon icon-xl"><use href="#icon-shield"/></svg>
                    <h3>暂无角色</h3>
                  </div>
                  <table v-else class="permission-table">
                    <thead>
                      <tr>
                        <th>角色名称</th>
                        <th>角色编码</th>
                        <th>描述</th>
                        <th>权限数</th>
                        <th>状态</th>
                        <th>创建时间</th>
                        <th>操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="r in permissionRoles" :key="r.id">
                        <td><strong>{{ r.name }}</strong></td>
                        <td><code>{{ r.code }}</code></td>
                        <td>{{ r.description || '-' }}</td>
                        <td><span class="badge">{{ r.permission_ids.length }} 项</span></td>
                        <td><span class="status-dot" :class="r.status"></span>{{ r.status==='active'?'启用':'停用' }}</td>
                        <td>{{ r.created_at }}</td>
                        <td class="action-cell">
                          <button class="btn btn-sm btn-secondary" @click="openEditRoleModal(r)">
                            <svg class="icon"><use href="#icon-edit"/></svg>
                          </button>
                          <button class="btn btn-sm btn-danger" @click="deleteRole(r.id)">
                            <svg class="icon"><use href="#icon-trash"/></svg>
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- 权限配置 -->
                <div v-if="permissionTab==='permissions'" class="tab-content active">
                  <div class="tab-header">
                    <span class="tab-count">共 {{ allPermissions.length }} 个权限</span>
                    <div>
                      <button class="btn btn-secondary btn-sm" @click="initDefaultPermissions" style="margin-right: 8px;">
                        <svg class="icon"><use href="#icon-redo"/></svg> 初始化默认权限
                      </button>
                      <button class="btn btn-primary btn-sm" @click="openAddPermissionModal">
                        <svg class="icon"><use href="#icon-plus"/></svg> 添加权限
                      </button>
                    </div>
                  </div>
                  <div v-if="allPermissions.length===0" class="empty-state">
                    <svg class="icon icon-xl"><use href="#icon-shield"/></svg>
                    <h3>暂无权限</h3>
                    <p>点击上方按钮添加权限或初始化默认权限</p>
                  </div>
                  <table v-else class="permission-table">
                    <thead>
                      <tr>
                        <th>权限标识</th>
                        <th>权限名称</th>
                        <th>类型</th>
                        <th>菜单路径</th>
                        <th>状态</th>
                        <th>操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="perm in allPermissions" :key="perm.id">
                        <td><code>{{ perm.key }}</code></td>
                        <td>{{ perm.name }}</td>
                        <td>
                          <span v-if="perm.is_menu" class="badge badge-info">菜单</span>
                          <span v-else class="badge badge-secondary">功能</span>
                        </td>
                        <td>
                          <span v-if="perm.is_menu">{{ perm.menu_path }}</span>
                          <span v-else class="text-muted">-</span>
                        </td>
                        <td>
                          <span v-if="perm.status === 'active'" class="badge badge-success">启用</span>
                          <span v-else class="badge badge-danger">停用</span>
                        </td>
                        <td class="action-cell">
                          <button class="btn btn-sm btn-secondary" @click="openEditPermissionModal(perm)">
                            <svg class="icon"><use href="#icon-edit"/></svg>
                          </button>
                          <button class="btn btn-sm btn-danger" @click="deletePermission(perm.id)">
                            <svg class="icon"><use href="#icon-trash"/></svg>
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

        </main>
      </div>

      <!-- 创建/编辑Agent弹窗 -->
      <div v-if="showCreateAgentModal" class="modal active" id="agent-modal">
        <div class="modal-overlay" id="agent-modal-overlay"></div>
        <div class="modal-content" id="agent-modal-content">
          <div class="modal-header">
            <h3>{{ isEditingAgent ? '编辑Agent' : '创建新Agent' }}</h3>
            <button class="modal-close" @click="closeCreateAgentModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Agent名称 <span class="required">*</span></label>
              <input type="text" class="form-input" v-model="agentForm.name" placeholder="输入Agent名称">
            </div>
            <div class="form-group">
              <label>描述</label>
              <textarea class="form-textarea" v-model="agentForm.description" placeholder="输入Agent描述"></textarea>
            </div>
            <div class="form-group">
              <label>可见范围 <span class="required">*</span></label>
              <select class="form-input" v-model="agentForm.agentSpace">
                <option value="private">私有 (仅自己可见)</option>
                <option value="group">部门 (同部门可见)</option>
                <option value="public">公开 (所有人可见)</option>
              </select>
              <small class="form-help">{{ agentForm.agentSpace === 'private' ? '只有您自己可以查看和使用此智能体' : agentForm.agentSpace === 'group' ? '同部门成员可以查看和使用此智能体' : '所有用户都可以查看和使用此智能体' }}</small>
            </div>
            <div class="form-group" v-if="!isEditingAgent || agentForm.createdBy === currentUser?.user_id">
              <label class="checkbox-label">
                <input type="checkbox" v-model="agentForm.isLocked">
                <span>锁定配置</span>
              </label>
              <small class="form-help">{{ agentForm.isLocked ? '开启后，仅创建者可以修改此智能体的配置' : '关闭时，所有有权限的用户都可以修改配置' }}</small>
            </div>
            <div class="form-group" v-else-if="isEditingAgent && agentForm.isLocked">
              <label class="checkbox-label" style="opacity: 0.6; cursor: not-allowed;">
                <input type="checkbox" checked disabled>
                <span>已锁定配置</span>
              </label>
              <small class="form-help">仅创建者可以修改此锁定状态</small>
            </div>
            <div class="form-group">
              <label>选择Skills</label>
              <div class="skill-chips" style="margin-bottom:8px" v-if="agentForm.skills.length > 0">
                <div v-for="id in agentForm.skills" :key="id" class="skill-chip">
                  {{ getSkillName(id) }}
                  <span class="skill-chip-remove" @click="toggleAgentSkill(id)">×</span>
                </div>
              </div>
              <div class="skill-dropdown" v-click-outside="() => createSkillDropdown = false">
                <div class="skill-dropdown-trigger" @click="createSkillDropdown = !createSkillDropdown">
                  <span>{{ agentForm.skills.length ? '已选 ' + agentForm.skills.length + ' 个技能' : '— 选择技能 —' }}</span>
                  <svg class="icon" style="width:14px;height:14px;transition:transform .2s" :style="createSkillDropdown ? 'transform:rotate(180deg)' : ''"><use href="#icon-chevron-down"/></svg>
                </div>
                <div class="skill-dropdown-menu" v-if="createSkillDropdown">
                  <div class="skill-dropdown-search">
                    <input type="text" placeholder="搜索技能..." v-model="createSkillSearch" class="skill-dropdown-input" @click.stop>
                  </div>
                  <div class="skill-dropdown-list">
                    <div v-if="filteredCreateSkills.length === 0" class="skill-empty">暂无匹配技能</div>
                    <div v-for="skill in filteredCreateSkills" :key="skill.id"
                         class="skill-dropdown-item"
                         :class="{ selected: agentForm.skills.includes(skill.id) }"
                         @click.stop="toggleAgentSkill(skill.id)">
                      <span class="skill-dropdown-check">{{ agentForm.skills.includes(skill.id) ? '✓' : '' }}</span>
                      <span>{{ skill.name }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="form-group">
              <label>选择工具 (MCP)</label>
              <div class="skill-chips" style="margin-bottom:8px" v-if="agentForm.tools.length > 0">
                <div v-for="toolId in agentForm.tools" :key="toolId" class="skill-chip">
                  {{ availableTools.find(t => t.id === toolId)?.name || toolId }}
                  <span class="skill-chip-remove" @click="toggleAgentTool(toolId)">×</span>
                </div>
              </div>
              <div class="skill-dropdown" v-click-outside="() => createToolDropdown = false">
                <div class="skill-dropdown-trigger" @click="createToolDropdown = !createToolDropdown">
                  <span>{{ agentForm.tools.length ? '已选 ' + agentForm.tools.length + ' 个工具' : '— 选择工具 —' }}</span>
                  <svg class="icon" style="width:14px;height:14px;transition:transform .2s" :style="createToolDropdown ? 'transform:rotate(180deg)' : ''"><use href="#icon-chevron-down"/></svg>
                </div>
                <div class="skill-dropdown-menu" v-if="createToolDropdown">
                  <div class="skill-dropdown-search">
                    <input type="text" placeholder="搜索工具..." v-model="createToolSearch" class="skill-dropdown-input" @click.stop>
                  </div>
                  <div class="skill-dropdown-list">
                    <div v-if="filteredCreateTools.length === 0" class="skill-empty">暂无匹配工具</div>
                    <div v-for="tool in filteredCreateTools" :key="tool.id"
                         class="skill-dropdown-item"
                         :class="{ selected: agentForm.tools.includes(tool.id) }"
                         @click.stop="toggleAgentTool(tool.id)">
                      <span class="skill-dropdown-check">{{ agentForm.tools.includes(tool.id) ? '✓' : '' }}</span>
                      <span>{{ tool.name }} <small style="color:#999">({{ tool.mcp_name }})</small></span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="form-group">
              <label>选择模型</label>
              <select class="form-input" v-model="agentForm.modelId">
                <option value="">— 选择模型 —</option>
                <option v-for="model in availableModels" :key="model.id" :value="model.id">
                  {{ model.name }} ({{ model.provider }}) {{ model.status === 'active' ? '✓' : '⚠' }}
                </option>
              </select>
              <small class="form-help" v-if="agentForm.modelId">
                已选择: {{ availableModels.find(m => m.id === agentForm.modelId)?.model_name || '' }}
                <span v-if="availableModels.find(m => m.id === agentForm.modelId)?.status !== 'active'" style="color: #f59e0b;">(未激活)</span>
              </small>
            </div>

            <div class="form-group">
              <label>选择提示词</label>
              <div class="skill-chips" style="margin-bottom:8px" v-if="agentForm.promptId">
                <div class="skill-chip">
                  {{ availablePrompts.find(p => p.id === agentForm.promptId)?.name || agentForm.promptId }}
                  <span class="skill-chip-remove" @click="clearCreatePrompt">×</span>
                </div>
              </div>
              <div class="skill-dropdown" v-click-outside="() => createPromptDropdown = false">
                <div class="skill-dropdown-trigger" @click="createPromptDropdown = !createPromptDropdown">
                  <span>{{ agentForm.promptId ? '更换提示词' : '— 选择提示词 —' }}</span>
                  <svg class="icon" style="width:14px;height:14px;transition:transform .2s" :style="createPromptDropdown ? 'transform:rotate(180deg)' : ''"><use href="#icon-chevron-down"/></svg>
                </div>
                <div class="skill-dropdown-menu" v-if="createPromptDropdown">
                  <div class="skill-dropdown-search">
                    <input type="text" placeholder="搜索提示词..." v-model="createPromptSearch" class="skill-dropdown-input" @click.stop>
                  </div>
                  <div class="skill-dropdown-list">
                    <div v-if="filteredCreatePrompts.length === 0" class="skill-empty">暂无匹配提示词</div>
                    <div v-for="prompt in filteredCreatePrompts" :key="prompt.id"
                         class="skill-dropdown-item"
                         :class="{ selected: agentForm.promptId === prompt.id }"
                         @click.stop="selectCreatePrompt(prompt)">
                      <span class="skill-dropdown-check">{{ agentForm.promptId === prompt.id ? '✓' : '' }}</span>
                      <span>{{ prompt.name }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <small class="form-help" v-if="agentForm.promptId">
                已选择提示词: {{ availablePrompts.find(p => p.id === agentForm.promptId)?.name || '' }}
              </small>
            </div>
</div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showCreateAgentModal=false">取消</button>
            <button class="btn btn-primary" @click="saveAgent">{{ isEditingAgent ? '保存' : '创建' }}</button>
          </div>
        </div>
      </div>

      <!-- 创建Skill弹窗 -->
      <div v-if="showCreateSkillModal" class="modal active" @click="creatingSkill || (showCreateSkillModal=false)">
        <div class="modal-overlay"></div>
        <div class="modal-content" style="position:relative" @click.stop>
          <div v-if="creatingSkill" class="modal-loading-overlay">
            <div class="modal-loading-spinner"></div>
            <p>正在创建Skill...</p>
          </div>
          <div class="modal-header">
            <h3>创建新Skill</h3>
            <button class="modal-close" @click="showCreateSkillModal=false">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Skill名称 <span class="required">*</span></label>
              <input type="text" class="form-input" v-model="skillForm.name" placeholder="输入Skill名称">
            </div>
            <div class="form-group">
              <label>描述</label>
              <textarea class="form-textarea" v-model="skillForm.description" placeholder="输入Skill描述"></textarea>
            </div>
            <div class="form-group">
              <label>可见范围 <span class="required">*</span></label>
              <select class="form-input" v-model="skillForm.skillSpace">
                <option value="private">私有 (仅自己可见)</option>
                <option value="group">部门 (同部门可见)</option>
                <option value="public">公开 (所有人可见)</option>
              </select>
              <small class="form-help">{{ skillForm.skillSpace === 'private' ? '只有您自己可以查看和使用此技能' : skillForm.skillSpace === 'group' ? '同部门成员可以查看和使用此技能' : '所有用户都可以查看和使用此技能' }}</small>
            </div>
            <div class="form-group">
              <label>Skill内容</label>
              <textarea class="form-textarea code-textarea" v-model="skillForm.code" placeholder="输入Skill内容" style="font-family:monospace;min-height:400px;height:400px"></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" :disabled="creatingSkill" @click="showCreateSkillModal=false">取消</button>
            <button class="btn btn-primary" :disabled="creatingSkill" @click="saveSkill">创建</button>
          </div>
        </div>
      </div>

      <!-- 编辑Skill弹窗 -->
      <div v-if="showEditSkillModal" class="modal active" @click="showEditSkillModal=false">
        <div class="modal-overlay"></div>
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h3>编辑Skill</h3>
            <button class="modal-close" @click="showEditSkillModal=false">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Skill名称 <span class="required">*</span></label>
              <input type="text" class="form-input" v-model="editSkillForm.name" placeholder="输入Skill名称">
            </div>
            <div class="form-group">
              <label>描述</label>
              <textarea class="form-textarea" v-model="editSkillForm.description" placeholder="输入Skill描述"></textarea>
            </div>
            <div class="form-group">
              <label>可见范围</label>
              <select class="form-input" v-model="editSkillForm.skillSpace">
                <option value="private">私有（仅自己可见）</option>
                <option value="group">部门内（同部门可见）</option>
                <option value="public">公开（所有人可见）</option>
              </select>
            </div>
            <div class="form-group">
              <label>Skill内容</label>
              <textarea class="form-textarea code-textarea" v-model="editSkillForm.code" placeholder="输入Skill内容" style="font-family:monospace;min-height:400px;height:400px"></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showEditSkillModal=false">取消</button>
            <button class="btn btn-primary" @click="saveEditSkill">保存</button>
          </div>
        </div>
      </div>

      <!-- 创建/编辑提示词模态框 -->
      <div v-if="showCreatePromptModal" class="modal active" @click="creatingPrompt || (showCreatePromptModal=false)">
        <div class="modal-overlay"></div>
        <div class="modal-content modal-large" @click.stop>
          <div class="modal-header">
            <h3>{{ isEditingPrompt ? '编辑提示词' : '创建提示词' }}</h3>
            <button class="modal-close" @click="showCreatePromptModal=false">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-row">
              <div class="form-group form-group-half">
                <label>提示词名称 <span class="required">*</span></label>
                <input type="text" class="form-input" v-model="promptForm.name" placeholder="输入提示词名称">
              </div>
              <div class="form-group form-group-half">
                <label>可见范围</label>
                <select class="form-input" v-model="promptForm.type">
                  <option value="private">私有（仅自己可见）</option>
                  <option value="group">部门内（同部门可见）</option>
                  <option value="public">公开（所有人可见）</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>描述</label>
              <input type="text" class="form-input" v-model="promptForm.description" placeholder="输入提示词描述">
            </div>
            <div class="form-group">
              <label>提示词内容 <span class="required">*</span></label>
              <textarea class="form-textarea code-textarea" v-model="promptForm.content"
                        placeholder="输入提示词内容"
                        style="font-family:monospace;min-height:300px;height:300px"></textarea>
            </div>
            <div class="form-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="promptForm.is_active"> 启用此提示词
              </label>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" :disabled="creatingPrompt" @click="showCreatePromptModal=false">取消</button>
            <button class="btn btn-primary" :disabled="creatingPrompt" @click="savePrompt">
              {{ creatingPrompt ? '保存中...' : (isEditingPrompt ? '保存' : '创建') }}
            </button>
          </div>
        </div>
      </div>

      <!-- 测试提示词模态框 -->
      <!-- 执行结果弹窗 -->
      <div v-if="showExecutionResultModal" class="modal active" @click="showExecutionResultModal=false">
        <div class="modal-overlay"></div>
        <div class="modal-content modal-large" @click.stop>
          <div class="modal-header">
            <h3>执行结果</h3>
            <button class="modal-close" @click="showExecutionResultModal=false">&times;</button>
          </div>
          <div class="modal-body" v-if="currentExecution">
            <div class="execution-status" :class="currentExecution.status">
              <svg class="icon" style="width:24px;height:24px"><use :href="currentExecution.status==='success'?'#icon-check-circle':'#icon-times-circle'"/></svg>
              <div><strong>{{ currentExecution.status==='success' ? '执行成功' : '执行失败' }}</strong></div>
            </div>
            <div class="execution-output">
              <label>输出结果</label>
              <pre class="code-block">{{ JSON.stringify(currentExecution.output, null, 2) }}</pre>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showExecutionResultModal=false">关闭</button>
          </div>
        </div>
      </div>

      <!-- MCP管理弹窗 -->
      <div v-if="showMcpModal" class="modal active" @click="showMcpModal=false">
        <div class="modal-overlay"></div>
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h3>{{ isEditingMcp ? '编辑MCP服务' : '添加MCP服务' }}</h3>
            <button class="modal-close" @click="showMcpModal=false">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>服务名称 <span class="required">*</span></label>
              <input type="text" class="form-input" v-model="mcpForm.name" placeholder="输入MCP服务名称">
            </div>
            <div class="form-group">
              <label>服务类型</label>
              <select class="form-input" v-model="mcpForm.type"><option value="sse">SSE (Server-Sent Events)</option><option value="stdio">StdIO (标准输入输出)</option><option value="streamable-http">HTTP Streamable</option></select>
            </div>
            <div class="form-group">
              <label>端点地址 <span class="required">*</span></label>
              <input type="text" class="form-input" v-model="mcpForm.endpoint" :placeholder="mcpForm.type==='sse'?'http://localhost:3001/mcp':mcpForm.type==='streamable-http'?'https://api.example.com/mcp':'node server.js'">
            </div>
            <div class="form-group">
              <label>可见性</label>
              <select class="form-input" v-model="mcpForm.visibility"><option value="public">公开（所有人可见）</option><option value="private">私有（仅自己可见）</option><option value="group">组内（同部门可见）</option></select>
            </div>
            <div class="form-group">
              <label>描述</label>
              <textarea class="form-textarea" v-model="mcpForm.description" placeholder="描述此MCP服务的功能"></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showMcpModal=false">取消</button>
            <button class="btn btn-primary" @click="saveMcpServer">{{ isEditingMcp ? '保存修改' : '添加' }}</button>
          </div>
        </div>
      </div>

      <!-- 模型管理弹窗 -->
      <div v-if="showModelModal" class="modal active" @click="showModelModal=false">
        <div class="modal-overlay"></div>
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h3>{{ isEditingModel ? '编辑模型' : '添加模型' }}</h3>
            <button class="modal-close" @click="showModelModal=false">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>显示名称 <span class="required">*</span></label>
              <input type="text" class="form-input" v-model="modelForm.name" placeholder="例如: GPT-4o">
            </div>
            <div class="form-group">
              <label>模型类型 <span class="required">*</span></label>
              <select class="form-input" v-model="modelForm.modelType">
                <option value="chat">Chat模型</option>
                <option value="embedding">Embedding模型</option>
                <option value="huggingface">HuggingFace模型</option>
              </select>
            </div>
            <div class="form-group">
              <label>提供商</label>
              <select class="form-input" v-model="modelForm.provider">
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="azure">Azure OpenAI</option>
                <option value="ollama">Ollama</option>
                <option value="huggingface">HuggingFace</option>
                <option value="custom">自定义</option>
              </select>
            </div>
            <div class="form-group">
              <label>模型ID <span class="required">*</span></label>
              <input type="text" class="form-input" v-model="modelForm.modelName" placeholder="例如: gpt-4o, text-embedding-3-small, bert-base-chinese">
            </div>
            <div class="form-group">
              <label>接口地址</label>
              <input type="text" class="form-input" v-model="modelForm.baseUrl" placeholder="例如: https://api.openai.com/v1">
            </div>
            <div class="form-group">
              <label>API密钥</label>
              <input type="password" class="form-input" v-model="modelForm.apiKey" placeholder="输入API密钥">
            </div>
            <div class="form-group">
              <label>描述</label>
              <textarea class="form-textarea" v-model="modelForm.description" placeholder="描述此模型的用途"></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showModelModal=false">取消</button>
            <button class="btn btn-primary" @click="saveModel">{{ isEditingModel ? '保存修改' : '添加' }}</button>
          </div>
        </div>
      </div>

      <!-- 部门管理弹窗 -->
      <div v-if="showDepartmentModal" class="modal active" @click="showDepartmentModal=false">
        <div class="modal-overlay"></div>
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h3>{{ isEditingDepartment ? '编辑部门' : '添加部门' }}</h3>
            <button class="modal-close" @click="showDepartmentModal=false">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>部门名称 <span class="required">*</span></label>
              <input type="text" class="form-input" v-model="departmentForm.name" placeholder="输入部门名称">
            </div>
            <div class="form-group">
              <label>部门编码 <span class="required">*</span></label>
              <input type="text" class="form-input" v-model="departmentForm.code" placeholder="输入部门编码" :disabled="isEditingDepartment">
              <p class="form-hint">编码需唯一，建议使用英文</p>
            </div>
            <div class="form-group">
              <label>上级部门</label>
              <select class="form-input" v-model="departmentForm.parent_id">
                <option value="">无上级部门</option>
                <option v-for="d in departments.filter(x => x.id !== departmentForm.id)" :key="d.id" :value="d.id">{{ d.name }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>描述</label>
              <textarea class="form-textarea" v-model="departmentForm.description" placeholder="输入部门描述"></textarea>
            </div>
            <div class="form-group">
              <label>排序</label>
              <input type="number" class="form-input" v-model="departmentForm.sort_order" placeholder="排序号">
            </div>
            <div class="form-group">
              <label>状态</label>
              <select class="form-input" v-model="departmentForm.status">
                <option value="active">启用</option>
                <option value="inactive">停用</option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showDepartmentModal=false">取消</button>
            <button class="btn btn-primary" @click="saveDepartment">{{ isEditingDepartment ? '保存修改' : '添加' }}</button>
          </div>
        </div>
      </div>

      <!-- 用户管理弹窗 -->
      <div v-if="showUserModal" class="modal active" @click="showUserModal=false">
        <div class="modal-overlay"></div>
        <div class="modal-content" style="max-width: 600px;" @click.stop>
          <div class="modal-header">
            <h3>{{ isEditingUser ? '编辑用户' : '添加用户' }}</h3>
            <button class="modal-close" @click="showUserModal=false">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
              <div class="form-group">
                <label>用户名 <span class="required">*</span></label>
                <input type="text" class="form-input" v-model="userForm.username" placeholder="输入用户名">
              </div>
              <div class="form-group">
                <label>姓名</label>
                <input type="text" class="form-input" v-model="userForm.real_name" placeholder="输入真实姓名">
              </div>
            </div>
            <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
              <div class="form-group">
                <label>邮箱</label>
                <input type="email" class="form-input" v-model="userForm.email" placeholder="user@example.com">
              </div>
              <div class="form-group">
                <label>电话</label>
                <input type="text" class="form-input" v-model="userForm.phone" placeholder="输入电话号码">
              </div>
            </div>
            <div class="form-group" v-if="!isEditingUser">
              <label>密码 <span class="required">*</span></label>
              <input type="password" class="form-input" v-model="userForm.password" placeholder="输入密码">
            </div>
            <div class="form-group" v-if="isEditingUser">
              <label>密码（留空则不修改）</label>
              <input type="password" class="form-input" v-model="userForm.password" placeholder="输入新密码">
            </div>
            <div class="form-group">
              <label>所属部门</label>
              <select class="form-input" v-model="userForm.department_id">
                <option value="">请选择部门</option>
                <option v-for="d in departments" :key="d.id" :value="d.id">{{ d.name }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>角色</label>
              <div class="permission-checklist" style="max-height: 200px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: 6px; padding: 12px;">
                <div v-for="role in permissionRoles" :key="role.id" class="perm-check-item">
                  <label class="checkbox-label">
                    <input type="checkbox" :checked="userForm.role_ids.includes(role.id)" @change="
                      const idx = userForm.role_ids.indexOf(role.id);
                      if (idx > -1) userForm.role_ids.splice(idx, 1);
                      else userForm.role_ids.push(role.id);
                    ">
                    <span>{{ role.name }}</span>
                    <small style="color: var(--text-secondary); margin-left: 8px;">{{ role.description || '' }}</small>
                  </label>
                </div>
                <div v-if="permissionRoles.length === 0" style="color: var(--text-secondary); text-align: center; padding: 16px;">
                  暂无角色，请先创建角色
                </div>
              </div>
            </div>
            <div class="form-group">
              <label>状态</label>
              <select class="form-input" v-model="userForm.status">
                <option value="active">启用</option>
                <option value="inactive">停用</option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showUserModal=false">取消</button>
            <button class="btn btn-primary" @click="saveUser">{{ isEditingUser ? '保存修改' : '添加' }}</button>
          </div>
        </div>
      </div>

      <!-- 角色管理弹窗 -->
      <div v-if="showRoleModal" class="modal active" @click="showRoleModal=false">
        <div class="modal-overlay"></div>
        <div class="modal-content" style="max-width: 700px;" @click.stop>
          <div class="modal-header">
            <h3>{{ isEditingRole ? '编辑角色' : '添加角色' }}</h3>
            <button class="modal-close" @click="showRoleModal=false">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
              <div class="form-group">
                <label>角色名称 <span class="required">*</span></label>
                <input type="text" class="form-input" v-model="roleForm.name" placeholder="例如: 系统管理员">
              </div>
              <div class="form-group">
                <label>角色编码 <span class="required">*</span></label>
                <input type="text" class="form-input" v-model="roleForm.code" placeholder="例如: admin" :disabled="isEditingRole">
                <p class="form-hint">编码需唯一，建议使用英文</p>
              </div>
            </div>
            <div class="form-group">
              <label>描述</label>
              <textarea class="form-textarea" v-model="roleForm.description" placeholder="描述此角色的权限范围"></textarea>
            </div>
            <div class="form-group">
              <label>状态</label>
              <select class="form-input" v-model="roleForm.status">
                <option value="active">启用</option>
                <option value="inactive">停用</option>
              </select>
            </div>
            <div class="form-group">
              <label>权限配置</label>
              <div class="permission-checklist" style="max-height: 300px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: 6px; padding: 12px;">
                <div v-for="perm in allPermissions" :key="perm.id" class="perm-check-item">
                  <label class="checkbox-label" style="display: flex; align-items: center; gap: 8px;">
                    <input type="checkbox" :checked="roleForm.permission_ids.includes(perm.id)" @change="toggleRolePermission(perm.id)">
                    <span>{{ perm.name }}</span>
                    <small style="color: var(--text-secondary);">({{ perm.key }})</small>
                  </label>
                </div>
                <div v-if="allPermissions.length === 0" style="color: var(--text-secondary); text-align: center; padding: 16px;">
                  暂无权限，请先添加权限
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showRoleModal=false">取消</button>
            <button class="btn btn-primary" @click="saveRole">{{ isEditingRole ? '保存修改' : '添加' }}</button>
          </div>
        </div>
      </div>

      <!-- 创建/编辑权限弹窗 -->
      <div v-if="showPermissionModal" class="modal active" @click="showPermissionModal=false">
        <div class="modal-overlay"></div>
        <div class="modal-content" style="max-width: 600px;" @click.stop>
          <div class="modal-header">
            <h3>{{ isEditingPermission ? '编辑权限' : '添加权限' }}</h3>
            <button class="modal-close" @click="showPermissionModal=false">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>权限标识 <span class="required">*</span></label>
              <input type="text" class="form-input" v-model="permissionForm.key" placeholder="如: system:user:view" :disabled="isEditingPermission">
              <p class="form-hint">权限标识需唯一，建议使用英文和冒号</p>
            </div>
            <div class="form-group">
              <label>权限名称 <span class="required">*</span></label>
              <input type="text" class="form-input" v-model="permissionForm.name" placeholder="如: 查看用户">
            </div>
            <div class="form-group">
              <label class="flex items-center gap-2" style="cursor:pointer">
                <input type="checkbox" v-model="permissionForm.is_menu">
                <span>是否为菜单</span>
              </label>
            </div>
            <div class="form-group" v-if="permissionForm.is_menu">
              <label>菜单路径 <span class="required">*</span></label>
              <input type="text" class="form-input" v-model="permissionForm.menu_path" placeholder="如: agents">
              <p class="form-hint">对应前端页面标识</p>
            </div>
            <div class="form-group" v-if="permissionForm.is_menu">
              <label>菜单图标</label>
              <input type="text" class="form-input" v-model="permissionForm.menu_icon" placeholder="如: bot">
              <p class="form-hint">图标名称，参考Lucide图标库</p>
            </div>
            <div class="form-group" v-if="permissionForm.is_menu">
              <label>排序顺序</label>
              <input type="number" class="form-input" v-model="permissionForm.menu_order" placeholder="数字越小越靠前">
            </div>
            <div class="form-group">
              <label class="flex items-center gap-2" style="cursor:pointer">
                <input type="checkbox" v-model="permissionForm.status">
                <span>是否启用</span>
              </label>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showPermissionModal=false">取消</button>
            <button class="btn btn-primary" @click="savePermission">{{ isEditingPermission ? '保存修改' : '添加' }}</button>
          </div>
        </div>
      </div>

      <!-- 修改密码弹窗 -->
      <div v-if="showChangePasswordModal" class="modal active" @click="showChangePasswordModal=false">
        <div class="modal-overlay"></div>
        <div class="modal-content" style="max-width:400px" @click.stop>
          <div class="modal-header">
            <h3>修改密码</h3>
            <button class="modal-close" @click="showChangePasswordModal=false">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>原密码 <span class="required">*</span></label>
              <input type="password" class="form-input" v-model="changePasswordForm.oldPassword" placeholder="请输入原密码">
            </div>
            <div class="form-group">
              <label>新密码 <span class="required">*</span></label>
              <input type="password" class="form-input" v-model="changePasswordForm.newPassword" placeholder="请输入新密码（至少6位）">
            </div>
            <div class="form-group">
              <label>确认新密码 <span class="required">*</span></label>
              <input type="password" class="form-input" v-model="changePasswordForm.confirmPassword" placeholder="请再次输入新密码">
            </div>
            <div class="form-error" v-if="changePasswordError" style="color:var(--danger-color);font-size:13px;margin-top:8px">{{ changePasswordError }}</div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showChangePasswordModal=false">取消</button>
            <button class="btn btn-primary" @click="handleChangePassword" :disabled="changePasswordLoading">
              <span v-if="!changePasswordLoading">确认修改</span>
              <svg v-else class="icon icon-spinner spinning"><use href="#icon-spinner"/></svg>
            </button>
          </div>
        </div>
      </div>

      <!-- 知识库弹窗 -->
      <div v-if="showKbModal" class="modal active" @click="showKbModal=false">
        <div class="modal-overlay"></div>
        <div class="modal-content" style="max-width: 600px;" @click.stop>
          <div class="modal-header">
            <h3>{{ isEditingKb ? '编辑知识库' : '创建知识库' }}</h3>
            <button class="modal-close" @click="showKbModal=false">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>知识库名称 <span class="required">*</span></label>
              <input type="text" class="form-input" v-model="kbForm.name" placeholder="输入知识库名称">
            </div>
            <div class="form-group">
              <label>描述</label>
              <textarea class="form-textarea" v-model="kbForm.description" placeholder="输入知识库描述"></textarea>
            </div>
            <div class="form-group">
              <label>嵌入模型</label>
              <input type="text" class="form-input" v-model="kbForm.embedding_model" placeholder="如: text-embedding-3-small">
            </div>
            <div class="form-group">
              <label>可见范围 <span class="required">*</span></label>
              <select class="form-input" v-model="kbForm.type">
                <option value="private">私有（仅自己可见）</option>
                <option value="group">部门（同部门可见）</option>
                <option value="public">公开（所有人可见）</option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showKbModal=false">取消</button>
            <button class="btn btn-primary" @click="saveKnowledgeBase">{{ isEditingKb ? '保存修改' : '创建' }}</button>
          </div>
        </div>
      </div>

      <!-- 知识库文档弹窗 -->
      <div v-if="showKbDocModal" class="modal active" @click="showKbDocModal=false">
        <div class="modal-overlay"></div>
        <div class="modal-content" style="max-width: 600px;" @click.stop>
          <div class="modal-header">
            <h3>添加文档</h3>
            <button class="modal-close" @click="showKbDocModal=false">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>文档标题 <span class="required">*</span></label>
              <input type="text" class="form-input" v-model="kbDocForm.title" placeholder="输入文档标题">
            </div>
            <div class="form-group">
              <label>内容</label>
              <textarea class="form-textarea" v-model="kbDocForm.content" placeholder="输入文档内容" rows="8"></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showKbDocModal=false">取消</button>
            <button class="btn btn-primary" @click="saveKbDoc">保存</button>
          </div>
        </div>
      </div>

      <!-- 知识库详情弹窗 -->
      <div v-if="showKbDetailModal" class="modal active" @click="showKbDetailModal=false">
        <div class="modal-overlay"></div>
        <div class="modal-content kb-detail-modal" style="max-width: 800px;" @click.stop>
          <div class="modal-header">
            <div class="kb-detail-header">
              <h3>{{ currentKb?.name }}</h3>
              <span class="kb-type-badge" :class="currentKb?.type">{{ currentKb?.type==='public'?'公开':currentKb?.type==='group'?'部门':'私有' }}</span>
            </div>
            <button class="modal-close" @click="showKbDetailModal=false">&times;</button>
          </div>
          <div class="kb-detail-tabs">
            <button class="tab-btn" :class="{active:kbDetailTab==='upload'}" @click="kbDetailTab='upload'">
              <svg class="icon"><use href="#icon-upload"/></svg> 文件上传
            </button>
            <button class="tab-btn" :class="{active:kbDetailTab==='test'}" @click="kbDetailTab='test'">
              <svg class="icon"><use href="#icon-search"/></svg> 命中测试
            </button>
          </div>
          <div class="modal-body">
            <!-- 文件上传标签页 -->
            <div v-if="kbDetailTab==='upload'" class="kb-upload-section">
              <div class="upload-area">
                <input type="file" id="kb-file-input" multiple style="display:none" @change="handleKbFileSelect">
                <label for="kb-file-input" class="upload-dropzone">
                  <svg class="icon icon-xl"><use href="#icon-upload"/></svg>
                  <p>点击或拖拽文件到此处上传</p>
                  <span class="upload-hint">支持 PDF、Word、TXT、Markdown 等格式</span>
                </label>
              </div>
              <div v-if="kbUploadFiles.length > 0" class="upload-file-list">
                <div v-for="(file, index) in kbUploadFiles" :key="index" class="upload-file-item">
                  <div class="file-info">
                    <svg class="icon"><use href="#icon-database"/></svg>
                    <div class="file-meta">
                      <span class="file-name">{{ file.name }}</span>
                      <span class="file-size">{{ formatFileSize(file.size) }}</span>
                    </div>
                  </div>
                  <div class="file-status">
                    <div v-if="file.status === 'pending'" class="status-pending">待上传</div>
                    <div v-else-if="file.status === 'uploading'" class="status-uploading">
                      <div class="progress-bar">
                        <div class="progress-fill" :style="{width: file.progress + '%'}"></div>
                      </div>
                      <span>{{ file.progress }}%</span>
                    </div>
                    <div v-else-if="file.status === 'success'" class="status-success">
                      <svg class="icon"><use href="#icon-check-circle"/></svg>
                    </div>
                    <div v-else-if="file.status === 'error'" class="status-error">
                      <svg class="icon"><use href="#icon-times-circle"/></svg>
                    </div>
                    <button v-if="file.status === 'pending'" class="btn-icon" @click="removeKbUploadFile(index)">
                      <svg class="icon"><use href="#icon-close"/></svg>
                    </button>
                  </div>
                </div>
              </div>
              <div v-if="kbUploadFiles.length > 0" class="upload-actions">
                <button class="btn btn-primary" @click="uploadKbFiles" :disabled="!kbUploadFiles.some(f => f.status === 'pending')">
                  <svg class="icon"><use href="#icon-upload"/></svg> 开始上传
                </button>
              </div>
            </div>
            <!-- 命中测试标签页 -->
            <div v-if="kbDetailTab==='test'" class="kb-test-section">
              <div class="test-input-area">
                <textarea class="form-textarea" v-model="kbTestQuery" placeholder="输入测试查询内容，测试知识库检索效果..." rows="3"></textarea>
                <button class="btn btn-primary" @click="testKbRetrieval" :disabled="kbTestLoading || !kbTestQuery.trim()">
                  <svg v-if="!kbTestLoading" class="icon"><use href="#icon-search"/></svg>
                  <svg v-else class="icon icon-spinner spinning"><use href="#icon-spinner"/></svg>
                  {{ kbTestLoading ? '测试中...' : '开始测试' }}
                </button>
              </div>
              <div v-if="kbTestResults.length > 0" class="test-results">
                <h4>检索结果</h4>
                <div v-for="(result, index) in kbTestResults" :key="index" class="test-result-item">
                  <div class="result-score">
                    <span class="score-badge" :class="result.score >= 0.8 ? 'high' : result.score >= 0.6 ? 'medium' : 'low'">
                      {{ (result.score * 100).toFixed(1) }}%
                    </span>
                    <span class="result-source">{{ result.source }}</span>
                  </div>
                  <p class="result-content">{{ result.content }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Toast通知 -->
      <div class="toast-container">
        <div v-for="toast in toasts" :key="toast.id" class="toast" :class="toast.type" style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <svg class="icon"><use :href="toast.type==='success'?'#icon-check-circle':toast.type==='error'?'#icon-times-circle':'#icon-info-circle'"/></svg>
          {{ toast.message }}
        </div>
      </div>
      </template>
    </div>
    `}).directive('click-outside', {
    mounted(el, binding) {
        el._clickOutside = (e) => { if (!el.contains(e.target)) binding.value(e); };
        document.addEventListener('click', el._clickOutside);
    },
    unmounted(el) {
        document.removeEventListener('click', el._clickOutside);
    }
}).mount('#app');
