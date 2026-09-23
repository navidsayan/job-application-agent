const jobList = document.querySelector('#job-list');
const feedback = document.querySelector('#feedback');
const refreshButton = document.querySelector('#refresh-button');
const searchInput = document.querySelector('#search-input');
const sourceFilter = document.querySelector('#source-filter');
const scoreFilter = document.querySelector('#score-filter');
const sortSelect = document.querySelector('#sort-select');
const filterCount = document.querySelector('#filter-count');
const discoveryForm = document.querySelector('#discovery-form');
const discoverySource = document.querySelector('#discovery-source');
const sourceIdentifier = document.querySelector('#source-identifier');
const sourceLabel = document.querySelector('#board-field');
let applications = [];

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
        <details class="job-details">
          <summary>Inspect listing</summary>
          <p>${escapeHtml(job.description || 'No description supplied by this source.')}</p>
          <div class="detail-grid">
            <span><strong>Required</strong> ${escapeHtml([...job.required_skills].join(', ') || 'Not specified')}</span>
            <span><strong>Preferred</strong> ${escapeHtml([...job.preferred_skills].join(', ') || 'Not specified')}</span>
          </div>
          <a class="listing-link" href="${escapeHtml(job.url)}" target="_blank" rel="noreferrer">Open original listing ↗</a>
          ${application.tailored_resume || application.cover_letter ? `<div class="drafts"><strong>Saved drafts</strong>${application.tailored_resume ? `<p>${escapeHtml(application.tailored_resume)}</p>` : ''}${application.cover_letter ? `<p>${escapeHtml(application.cover_letter)}</p>` : ''}</div>` : ''}
        </details>
      </div>
      <div class="score-block">
        <div class="score">${Math.round(match.score * 100)}%</div>
        <span class="score-label">Match score</span>
        <button class="approve-button" data-job-id="${escapeHtml(application.job_id)}" type="button">Approve</button>
        <button class="reject-button" data-job-id="${escapeHtml(application.job_id)}" type="button">Reject</button>
      </div>
    </article>`;
  }).join('');

  document.querySelectorAll('.approve-button').forEach((button) => {
    button.addEventListener('click', () => approve(button.dataset.jobId, button));
  });
  document.querySelectorAll('.reject-button').forEach((button) => {
    button.addEventListener('click', () => reject(button.dataset.jobId, button));
  });
}

function filteredApplications() {
  const query = searchInput.value.trim().toLowerCase();
  const source = sourceFilter.value;
  const minimumScore = Number(scoreFilter.value);
  const filtered = applications.filter((application) => {
    const { job, match } = application;
    const searchable = [job.title, job.company, job.location, job.description, ...match.matched_skills].join(' ').toLowerCase();
    return (!query || searchable.includes(query)) && (source === 'all' || job.source === source) && match.score >= minimumScore;
  });
  filtered.sort((left, right) => {
    if (sortSelect.value === 'title') return left.job.title.localeCompare(right.job.title);
    if (sortSelect.value === 'company') return left.job.company.localeCompare(right.job.company);
    if (sortSelect.value === 'source') return left.job.source.localeCompare(right.job.source);
    return right.match.score - left.match.score;
  });
  return filtered;
}

function renderFilteredJobs() {
  const filtered = filteredApplications();
  filterCount.textContent = `${filtered.length} of ${applications.length} shown`;
  renderJobs(filtered);
}

async function loadReviews() {
  refreshButton.disabled = true;
  try {
    const response = await fetch('/api/reviews');
    if (!response.ok) throw new Error('Unable to load the review queue.');
    applications = await response.json();
    renderSummary(applications);
    const sources = [...new Set(applications.map((item) => item.job.source))].sort();
    sourceFilter.innerHTML = '<option value="all">All sources</option>' + sources.map((source) => `<option value="${escapeHtml(source)}">${escapeHtml(source)}</option>`).join('');
    renderFilteredJobs();
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

async function reject(jobId, button) {
  button.disabled = true;
  try {
    const response = await fetch(`/api/applications/${encodeURIComponent(jobId)}/reject`, { method: 'POST' });
    if (!response.ok) throw new Error('Rejection could not be recorded.');
    feedback.hidden = false;
    feedback.textContent = `Application ${jobId} rejected.`;
    await loadReviews();
  } catch (error) {
    feedback.hidden = false;
    feedback.textContent = error.message;
    button.disabled = false;
  }
}

async function discover(event) {
  event.preventDefault();
  const source = discoverySource.value;
  const identifier = sourceIdentifier.value.trim();
  const payload = source === 'all-public' || source === 'arbeitnow' || source === 'remotive'
    ? { source }
    : ['greenhouse', 'ashby'].includes(source)
    ? { source, board: identifier }
    : source === 'lever'
      ? { source, site: identifier }
      : ['smartrecruiters', 'recruitee'].includes(source)
        ? { source, company: identifier }
        : { source, path: identifier };
  const button = discoveryForm.querySelector('button');
  button.disabled = true;
  button.textContent = 'Fetching...';
  try {
    const response = await fetch('/api/discover', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Discovery failed.');
    feedback.hidden = false;
    feedback.textContent = `Fetched ${result.count} matching listing${result.count === 1 ? '' : 's'}.`;
    await loadReviews();
  } catch (error) {
    feedback.hidden = false;
    feedback.textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = 'Fetch listings';
  }
}

refreshButton.addEventListener('click', loadReviews);
discoveryForm.addEventListener('submit', discover);
discoverySource.addEventListener('change', () => {
  const source = discoverySource.value;
  const globalSource = ['all-public', 'arbeitnow', 'remotive'].includes(source);
  const board = ['greenhouse', 'ashby'].includes(source);
  const lever = source === 'lever';
  const company = ['smartrecruiters', 'recruitee'].includes(source);
  sourceLabel.hidden = globalSource;
  sourceIdentifier.required = !globalSource;
  sourceLabel.firstChild.textContent = board ? 'Board slug' : lever ? 'Site slug' : company ? 'Company slug' : 'JSON path';
  sourceIdentifier.placeholder = board ? 'e.g. stripe' : lever ? 'e.g. netflix' : company ? 'e.g. acme' : 'e.g. jobs.example.json';
});
discoverySource.dispatchEvent(new Event('change'));
searchInput.addEventListener('input', renderFilteredJobs);
sourceFilter.addEventListener('change', renderFilteredJobs);
scoreFilter.addEventListener('change', renderFilteredJobs);
sortSelect.addEventListener('change', renderFilteredJobs);
loadReviews();
