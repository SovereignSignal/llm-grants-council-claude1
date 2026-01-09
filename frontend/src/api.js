/**
 * API client for the Agentic Grants Council backend.
 */

const API_BASE = 'http://localhost:8002';

export const api = {
  // ============================================
  // Grants Council API
  // ============================================

  /**
   * List all applications.
   */
  async listApplications() {
    const response = await fetch(`${API_BASE}/api/applications`);
    if (!response.ok) throw new Error('Failed to list applications');
    return response.json();
  },

  /**
   * Get a specific application with full evaluation.
   */
  async getApplication(id) {
    const response = await fetch(`${API_BASE}/api/applications/${id}`);
    if (!response.ok) throw new Error('Failed to get application');
    return response.json();
  },

  /**
   * Submit a new application.
   */
  async submitApplication(content, source = 'web', sourceId = null) {
    const response = await fetch(`${API_BASE}/api/applications`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, source, source_id: sourceId }),
    });
    if (!response.ok) throw new Error('Failed to submit application');
    return response.json();
  },

  /**
   * Submit application with streaming updates.
   */
  async submitApplicationStream(content, source, sourceId, onEvent) {
    const response = await fetch(`${API_BASE}/api/applications/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, source, source_id: sourceId }),
    });
    if (!response.ok) throw new Error('Failed to submit application');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },

  /**
   * Record a human decision on an application.
   */
  async recordDecision(applicationId, decision, notes = '') {
    const response = await fetch(
      `${API_BASE}/api/applications/${applicationId}/decision`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, notes }),
      }
    );
    if (!response.ok) throw new Error('Failed to record decision');
    return response.json();
  },

  /**
   * Record a grant outcome.
   */
  async recordOutcome(applicationId, outcome) {
    const response = await fetch(
      `${API_BASE}/api/applications/${applicationId}/outcome`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(outcome),
      }
    );
    if (!response.ok) throw new Error('Failed to record outcome');
    return response.json();
  },

  /**
   * List all teams.
   */
  async listTeams() {
    const response = await fetch(`${API_BASE}/api/teams`);
    if (!response.ok) throw new Error('Failed to list teams');
    return response.json();
  },

  /**
   * Get a specific team.
   */
  async getTeam(id) {
    const response = await fetch(`${API_BASE}/api/teams/${id}`);
    if (!response.ok) throw new Error('Failed to get team');
    return response.json();
  },

  /**
   * List observations with optional filters.
   */
  async listObservations(agentId = null, status = null) {
    const params = new URLSearchParams();
    if (agentId) params.append('agent_id', agentId);
    if (status) params.append('status', status);
    const url = `${API_BASE}/api/observations${params.toString() ? '?' + params : ''}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to list observations');
    return response.json();
  },

  /**
   * Approve a draft observation.
   */
  async approveObservation(id) {
    const response = await fetch(`${API_BASE}/api/observations/${id}/approve`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to approve observation');
    return response.json();
  },

  /**
   * Deprecate an observation.
   */
  async deprecateObservation(id) {
    const response = await fetch(`${API_BASE}/api/observations/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to deprecate observation');
    return response.json();
  },

  /**
   * List all agents.
   */
  async listAgents() {
    const response = await fetch(`${API_BASE}/api/agents`);
    if (!response.ok) throw new Error('Failed to list agents');
    return response.json();
  },

  // ============================================
  // Legacy Conversation API
  // ============================================
  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`);
    if (!response.ok) {
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation() {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, onEvent) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },
};
