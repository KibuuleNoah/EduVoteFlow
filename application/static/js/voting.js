let idx = 0;
var candidates = null;
var posts = null;

function loadCandidates(candidates) {
  candidates = candidates;
}

function NextBallot() {
  if (idx > 0) {
    castVote();
    if (idx == posts.length) {
      window.location.href = "/auth/logout";
    }
  }

  if (!candidates) {
    candidatesInput = document.getElementById("candidates");
    candidates = JSON.parse(candidatesInput.value);
    posts = Object.keys(candidates);
  }
  const ballot = document.getElementById("ballot");

  // Fade out the current content
  ballot.classList.add("fade-out");

  // Wait for the fade-out transition to complete
  setTimeout(() => {
    // Replace the content
    let newBallotContent = "";

    for (let candidate of candidates[posts[idx]]) {
      newBallotContent += `
        <div class="col-6 col-md-4 col-3 mb-2">
          <div class="card bg-dark rounded">
            <div class="card-header">
              <img class="img-fluid rounded-circle" src="${candidate.logo}" style="width:8rem;height:8rem;">
            </div>
            <div class="card-body">
              <h6 class="card-title d-md-none">${candidate.names} <br> <small>${candidate.slogan}</small> </h6>
              <h3 class="card-title d-none d-md-block">${candidate.names} <br> <small>${candidate.slogan}</small> </h3>
              <div class="form-check">
                <input class="form-check-input" type="radio" name="vote" id="" value="${candidate.id}">
                <label class="form-check-label" for="">VOTE</label>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    ballot.innerHTML = `
  <div class="card rounded mb-2 bg-dark">
    <h3 class="">${posts[idx]}</h3>
    <div class="row">
      ${newBallotContent}
    </div>
    <button type="button" class="btn btn-outline-info" style="width: 100%;" id="cast-vote"  onclick="NextBallot();" disabled>Cast Vote</button>
  </div>
  `;

    // Remove fade-out class and add fade-in class for the new content
    ballot.classList.remove("fade-out");
    ballot.classList.add("fade-in");
    voteListener();
    idx++;
  }, 500); // 500ms should match the CSS transition duration
  ballot.classList.remove("fade-in");
}

function castVote() {
  const votedCandidate = document.querySelector(
    'input[type="radio"][name="vote"]:checked',
  );

  var candidateId = votedCandidate.value;

  let urlInts = getIntegerParams(window.location.pathname);
  fetch(`/election/${urlInts[0]}/${urlInts[1]}/cast-vote`, {
    method: "POST",
    body: JSON.stringify({ candidateId: candidateId }),
  });
  // .then((response) => {
  //   if (response.ok) {
  //     alert(response.json());
  //   }
  // })
}

function voteListener() {
  const radioButtons = document.getElementsByName("vote");
  for (let radioButton of radioButtons) {
    radioButton.addEventListener("change", () => {
      document.getElementById("cast-vote").disabled = false;
    });
  }
}

function getIntegerParams(url) {
  const params = url.match(/(\d+)/g); // Regular expression to match one or more digits
  return params.map((param) => parseInt(param)); // Convert matches to integers
}
