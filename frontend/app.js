const jobList = document.querySelector('#job-list');
const feedback = document.querySelector('#feedback');
const refreshButton = document.querySelector('#refresh-button');

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[character]));
}

function renderSummary(applications) {
  document.querySelector('#review-count').textContent = applications.length;
  const topScore = applications.reduce((top, item) => Math.max(top, item.match.score), 0);
  document.querySelector('#top-score').textContent = applications.length ? `${Math.round(topScore * 100)}%` : '--';
  document.querySelector('#source-count').textContent = new Set(applications.map((item) => item.job.source)).size || '--';
}

function renderJobs(applications) {
  if (!applications.length) {
    jobList.innerHTML = '<div class="empty"><strong>Your review queue is clear.</strong>Run discovery to find new roles that fit your profile.</div>';
    return;
  }

  jobList.innerHTML = applications.map((application, index) => {
    const { job, match } = application;
    const skills = [...match.matched_skills].slice(0, 8).map((skill) => `<span class="chip">${escapeHtml(skill)}</span>`).join('');
    const reasons = match.reasons.map((reason) => `<span class="reason">${escapeHtml(reason)}</span>`).join('');
    return `<article class="job-card" style="animation-delay: ${index * 60}ms">
      <div>
        <div class="job-topline"><h3 class="job-title">${escapeHtml(job.title)}</h3><span class="source">${escapeHtml(job.source)}</span></div>
        <p class="job-company">${escapeHtml(job.company)} · ${escapeHtml(job.location)}</p>
        <div class="job-meta">${skills || '<span class="chip">Profile match</span>'}</div>
        <div class="reason-list">${reasons}</div>
      </div>
      <div class="score-block">
        <div class="score">${Math.round(match.score * 100)}%</div>
        <span class="score-label">Match score</span>
        <button class="approve-button" data-job-id="${escapeHtml(application.job_id)}" type="button">Approve</button>
      </div>
    </article>`;
  }).join('');

  document.querySelectorAll('.approve-button').forEach((button) => {
    button.addEventListener('click', () => approve(button.dataset.jobId, button));
  });
}

async function loadReviews() {
  refreshButton.disabled = true;
  try {
    const response = await fetch('/api/reviews');
    if (!response.ok) throw new Error('Unable to load the review queue.');
    const applications = await response.json();
    renderSummary(applications);
    renderJobs(applications);
    document.querySelector('#last-updated').textContent = `Updated ${new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`;
  } catch (error) {
    feedback.hidden = false;
    feedback.textContent = error.message;
  } finally {
    refreshButton.disabled = false;
  }
}

async function approve(jobId, button) {
  button.disabled = true;
  try {
    const response = await fetch(`/api/applications/${encodeURIComponent(jobId)}/approve`, { method: 'POST' });
    if (!response.ok) throw new Error('Approval could not be recorded.');
    feedback.hidden = false;
    feedback.textContent = `Application ${jobId} approved.`;
    await loadReviews();
  } catch (error) {
    feedback.hidden = false;
    feedback.textContent = error.message;
    button.disabled = false;
  }
}

refreshButton.addEventListener('click', loadReviews);
loadReviews();
