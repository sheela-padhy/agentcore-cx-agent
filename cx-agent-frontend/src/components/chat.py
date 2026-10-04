"""Chat components."""

import streamlit as st

from models.message import Message
from services.conversation_client import ConversationClient
from services.agentcore_client import AgentCoreClient
from typing import Union


def render_message(
    message: Message, client: Union[ConversationClient, AgentCoreClient] = None
):
    """Render a single message."""
    with st.chat_message(message.role):
        st.write(message.content)

        # Add feedback buttons for assistant messages
        if message.role == "assistant" and client:
            # Use message timestamp + content hash for unique ID
            unique_id = f"{message.timestamp.isoformat()}_{hash(message.content)}"
            message_id = str(message.metadata.get("message_id", unique_id))

            # Check if feedback already given
            feedback_key = f"feedback_given_{message_id}"
            if feedback_key not in st.session_state:
                st.session_state[feedback_key] = False

            if not st.session_state[feedback_key]:
                st.markdown("---")
                st.markdown("**Was this helpful?**")

                col1, col2, col3 = st.columns([2, 2, 6])

                with col1:
                    if st.button(
                        "👍 Helpful", key=f"up_{message_id}", use_container_width=True
                    ):
                        st.session_state[f"show_pos_form_{message_id}"] = True
                        st.rerun()

                    if st.session_state.get(f"show_pos_form_{message_id}", False):
                        feedback_text = st.text_input(
                            "What did you like? (optional)",
                            key=f"pos_text_{message_id}",
                            placeholder="What was helpful about this response?",
                        )
                        col_submit, col_cancel = st.columns([1, 1])
                        with col_submit:
                            if st.button(
                                "✓",
                                key=f"pos_submit_{message_id}",
                                type="primary",
                                help="Submit feedback",
                            ):
                                if client.submit_feedback(
                                    message_id,
                                    st.session_state.get("conversation_id", "default"),
                                    1.0,
                                    feedback_text,
                                ):
                                    st.session_state[feedback_key] = True
                                    st.session_state[f"show_pos_form_{message_id}"] = (
                                        False
                                    )
                                    st.success("✓ Thank you for your feedback!")
                                    st.rerun()
                        with col_cancel:
                            if st.button(
                                "✗", key=f"pos_cancel_{message_id}", help="Cancel"
                            ):
                                st.session_state[f"show_pos_form_{message_id}"] = False
                                st.rerun()

                with col2:
                    if st.button(
                        "👎 Not helpful",
                        key=f"down_{message_id}",
                        use_container_width=True,
                    ):
                        with st.expander("📝 Tell us more (optional)", expanded=True):
                            feedback_text = st.text_area(
                                "How can we improve?",
                                key=f"text_{message_id}",
                                placeholder="Your feedback helps us improve...",
                                height=80,
                            )
                            if st.button(
                                "📤 Submit Feedback",
                                key=f"submit_{message_id}",
                                type="primary",
                            ):
                                if client.submit_feedback(
                                    message_id,
                                    st.session_state.get("conversation_id", "default"),
                                    0.0,
                                    feedback_text,
                                ):
                                    st.session_state[feedback_key] = True
                                    st.success("✓ Thank you for your feedback!")
                                    st.rerun()
            else:
                st.markdown(
                    "<div style='color: #28a745; font-size: 0.9em;'>✓ Feedback submitted</div>",
                    unsafe_allow_html=True,
                )

        # Show citations if available
        if message.metadata and "citations" in message.metadata:
            import json

            try:
                citations_str = message.metadata["citations"]
                if isinstance(citations_str, str):
                    citations = json.loads(citations_str)
                else:
                    citations = citations_str

                if citations:
                    st.markdown("**📚 Sources:**")
                    for i, citation in enumerate(citations, 1):
                        with st.expander(
                            f"Source {i}: {citation.get('source', 'Unknown')}",
                            expanded=False,
                        ):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                if citation.get("s3_uri"):
                                    st.markdown(
                                        f"**📁 Document:** `{citation['s3_uri']}`"
                                    )
                            with col2:
                                if citation.get("relevance_score") is not None:
                                    score = float(citation["relevance_score"])
                                    st.metric("Relevance", f"{score:.2f}")
            except (json.JSONDecodeError, TypeError, KeyError):
                pass

        # Show tool calls if available
        if message.metadata and "tools_used" in message.metadata:
            tools_str = message.metadata["tools_used"]
            if tools_str:
                tools_used = [
                    tool.strip() for tool in tools_str.split(",") if tool.strip()
                ]
                if tools_used:
                    st.markdown("**🔧 Tools Used:**")
                    for tool in tools_used:
                        st.markdown(f"• `{tool}`")

        # Show metadata if available
        if message.metadata:
            with st.expander("Message Details", expanded=False):
                st.json(message.metadata)


def render_sidebar():
    """Render sidebar with configuration."""
    with st.sidebar:
        st.header("Configuration")

        # Model is fixed server-side (DEFAULT_MODEL on the Agent Runtime,
        # not a frontend choice), so there's nothing to pick here. This
        # placeholder is only ever used if a response genuinely doesn't
        # report its own model - see "Message Details" on each response
        # for what actually answered.
        model = "server-configured"
        st.caption("Model: configured server-side (see Message Details on each response)")

        # User ID
        user_id = st.text_input("User ID", value=st.session_state.user_id)
        st.session_state.user_id = user_id

        # Conversation controls
        st.header("Conversation")

        if st.button("New Conversation", type="primary"):
            st.session_state.conversation_id = None
            st.session_state.messages = []
            st.rerun()

        if st.session_state.conversation_id:
            st.success(f"Active: {st.session_state.conversation_id[:8]}...")

        return model
