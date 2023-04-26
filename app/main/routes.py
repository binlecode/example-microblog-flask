from datetime import datetime
from flask import render_template, flash, redirect, url_for
from flask import request
from flask import g
from flask import current_app
from flask_login import current_user
from flask_login import login_required
from app import db
from app.models import User, Post
from app.main.forms import EditProfileForm, PostForm
from app.main.forms import SearchForm
from app.main import bp


# before request interceptor
# updates current user's last_seen timestamp
# provide search form in g request scope, see: `app/templates/base.html`
#
@bp.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

        # Initialize SearchForm and attach to g container
        # Note that g context is request scope, so every incoming request
        # has a new SearchForm object that can be referred in different
        # view templates.
        # Only initialize SearchForm when elasticsearch is enabled
        if current_app.elasticsearch is not None:
            g.search_form = SearchForm()


@bp.route('/export_posts')
@login_required
def export_posts():
    if current_user.get_task_in_progress('export_posts'):
        flash('An export task is currently in progress')
    else:
        current_user.launch_task('export_posts', 'Exporting posts')
        db.session.commit()
    return redirect(url_for('main.user', username=current_user.username))


@bp.route('/search')
@login_required
def search():
    # use form.validate() which just validates field values, without checking
    # how the data was submitted
    # this is because search form is a GET request
    if not g.search_form.validate():
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    page_size = current_app.config.get('POSTS_PER_PAGE', 3)
    posts, total = Post.search(g.search_form.q.data, page, page_size)
    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * page_size else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('search.html', title='Search', posts=posts,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        return redirect(url_for('main.index'))

    # basic pagination,
    page = request.args.get('page', 1, type=int)
    page_size = current_app.config.get('POSTS_PER_PAGE', 3)
    posts_pg = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, page_size, False)

    prev_pg_url = url_for('main.index', page=posts_pg.prev_num) if posts_pg.has_prev else None
    next_pg_url = url_for('main.index', page=posts_pg.next_num) if posts_pg.has_next else None

    posts = posts_pg.items
    return render_template('index.html', title='Home', posts=posts, form=form,
                           prev_url=prev_pg_url, next_url=next_pg_url)


# route with url bind variable <username>, this is passed to
# the user() function as 'username' argument
@bp.route('/user/<username>')
def user(username):
    # first_or_404 is a variant of first(), when no record found
    # it will automatically send back a 404 response
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    page_size = current_app.config.get('POSTS_PER_PAGE', 3)
    posts_pg = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, page_size, False)

    prev_pg_url = url_for('user', username=username,
                          page=posts_pg.prev_num) if posts_pg.has_prev else None
    next_pg_url = url_for('user', username=username,
                          page=posts_pg.next_num) if posts_pg.has_next else None

    return render_template('user.html', user=user, posts=posts_pg.items,
                           prev_url=prev_pg_url, next_url=next_pg_url)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()  # current_user is already in db.session
        flash('Your profile has been saved')
        return redirect(url_for('main.edit_profile'))

    elif request.method == 'GET':
        # make sure to pre-populate initial value to Field.data attribute,
        # not field itself
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me

    return render_template('edit_profile.html', title='Edit Profile', form=form)
