import streamlit as st
import requests

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Smart Lock App", page_icon="🔐", layout="centered")

def init_state():
    defaults = {
        "screen": "login",          # login / register / locks / pair / detail
        "token": None,
        "username": None,
        "locks": [],
        "selected_lock": None,
        "message": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

def login_request(username: str, password: str):
    try:
        response = requests.post(
            f"{BACKEND_URL}/token",
            data={"username": username, "password": password},
            timeout=5,
            verify=False
        )
        if response.status_code == 200:
            return True, response.json()
        return False, response.text
    except Exception as e:
        return False, str(e)



def register_request(username: str, password: str, email: str):
    try:
        response = requests.post(
            f"{BACKEND_URL}/register",
            json={
                "username": username,
                "password": password,
                "email": email,
            },
            timeout=5,
            verify=False
        )
        if response.status_code in (200, 201):
            return True, response.json()
        return False, response.text
    except Exception as e:
        return False, str(e)



def get_my_locks(token: str):
    try:
        response = requests.get(
            f"{BACKEND_URL}/locks/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
            verify=False
        )
        if response.status_code == 200:
            return True, response.json()
        return False, response.text
    except Exception as e:
        return False, str(e)



def pair_lock(token: str, lock_id: int, password: str):
    try:
        response = requests.post(
            f"{BACKEND_URL}/lock/pairlock",
            headers={"Authorization": f"Bearer {token}"},
            json={"lock_id": lock_id, "password": password},
            timeout=5,
            verify=False
        )
        if response.status_code == 200:
            return True, response.json()
        return False, response.text
    except Exception as e:
        return False, str(e)



def get_lock_detail(token: str, lock_id: int):
    try:
        response = requests.get(
            f"{BACKEND_URL}/lock/{lock_id}/status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
            verify=False
        )
        if response.status_code == 200:
            return True, response.json()
        return False, response.text
    except Exception as e:
        return False, str(e)



def toggle_lock(token: str, lock_id: int):
    try:
        response = requests.post(
            f"{BACKEND_URL}/lock/toggle/{lock_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
            verify=False
        )
        if response.status_code == 200:
            return True, response.json()
        return False, response.text
    except Exception as e:
        return False, str(e)

def set_message(msg: str):
    st.session_state.message = msg

def show_message():
    if st.session_state.message:
        st.info(st.session_state.message)

def refresh_locks():
    if not st.session_state.token:
        return
    ok, result = get_my_locks(st.session_state.token)
    if ok:
        st.session_state.locks = result
    else:
        st.session_state.locks = []
        set_message(f"unable to get locks: {result}")

def screen_login():
    st.title("Smart Lock Login")
    show_message()

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        col1, col2 = st.columns(2)
        login_clicked = col1.form_submit_button("Login", use_container_width=True)
        register_clicked = col2.form_submit_button("Register", use_container_width=True)

    if login_clicked:
        ok, result = login_request(username, password)
        if ok:
            st.session_state.token = result.get("access_token")
            st.session_state.username = username
            refresh_locks()
            set_message("Login successful")
            st.session_state.screen = "locks"
            st.rerun()
        else:
            set_message(f"Login failed: {result}")
            st.rerun()

    if register_clicked:
        st.session_state.screen = "register"
        st.session_state.message = ""
        st.rerun()

def screen_register():
    st.title("Register")
    show_message()

    with st.form("register_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        email = st.text_input("Email")

        col1, col2 = st.columns(2)
        submit_clicked = col1.form_submit_button("Submit", use_container_width=True)
        back_clicked = col2.form_submit_button("Back", use_container_width=True)

    if submit_clicked:
        ok, result = register_request(username, password, email)
        if ok:
            set_message("Register successful, please login")
            st.session_state.screen = "login"
            st.rerun()
        else:
            set_message(f"Register failed: {result}")
            st.rerun()

    if back_clicked:
        st.session_state.screen = "login"
        st.session_state.message = ""
        st.rerun()

def screen_pair():
    st.title("Pair Lock")
    show_message()

    with st.form("pair_form"):
        lock_id = st.number_input("Lock ID", min_value=1, step=1)
        pair_password = st.text_input("Lock Password", type="password")

        col1, col2 = st.columns(2)
        submit_clicked = col1.form_submit_button("Pair", use_container_width=True)
        back_clicked = col2.form_submit_button("Back", use_container_width=True)

    if submit_clicked:
        ok, result = pair_lock(st.session_state.token, int(lock_id), pair_password)
        if ok:
            refresh_locks()
            set_message("Pair successful")
            st.session_state.screen = "locks"
            st.rerun()
        else:
            set_message(f"Pair failed: {result}")
            st.rerun()

    if back_clicked:
        st.session_state.screen = "locks"
        st.session_state.message = ""
        st.rerun()

def screen_locks():
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.title("My Locks")
        st.caption(f"Current user: {st.session_state.username}")
    with top_right:
        if st.button("Pair", use_container_width=True):
            st.session_state.screen = "pair"
            st.session_state.message = ""
            st.rerun()

    show_message()

    col1, col2 = st.columns(2)
    if col1.button("Refresh", use_container_width=True):
        refresh_locks()
        st.rerun()
    if col2.button("Logout", use_container_width=True):
        st.session_state.token = None
        st.session_state.username = None
        st.session_state.locks = []
        st.session_state.selected_lock = None
        st.session_state.screen = "login"
        st.session_state.message = "Logged out"
        st.rerun()

    locks = st.session_state.locks
    if not locks:
        st.warning("No paired locks yet")
        return

    for lock in locks:
        lock_id = lock.get("lock_id")
        status = lock.get("status", "unknown")

        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1.5])
            c1.write(f"**Lock ID:** {lock_id}")
            c2.write(f"**Status:** {status}")
            if c3.button("Toggle", key=f"toggle_{lock_id}", use_container_width=True):
                ok, result = toggle_lock(st.session_state.token, lock_id)
                if ok:
                    refresh_locks()
                    set_message(f"Lock {lock_id} toggled successfully")
                else:
                    set_message(f"Toggle failed: {result}")
                st.rerun()

def screen_detail():
    st.session_state.screen = "locks"
    st.rerun()
    
def main():
    screen = st.session_state.screen

    if screen == "login":
        screen_login()
    elif screen == "register":
        screen_register()
    elif screen == "locks":
        screen_locks()
    elif screen == "pair":
        screen_pair()
    elif screen == "detail":
        screen_detail()
    else:
        st.session_state.screen = "login"
        st.rerun()


if __name__ == "__main__":
    main()

