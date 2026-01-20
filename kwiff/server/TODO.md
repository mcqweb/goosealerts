When we receive a request json we need to do the following:
 Identify the match at BetFair & Smarkets
 Identify the player names to allow comparisons
 Store the IDs (players & matches) for BetFair, Smarkets & Kwiff

There will be a separate monitoring process running locally
 This will use the matches and ids to check for lay prices being available
 If a lay is available we will store it locally
  Include Timestamp, Odds, Size (Liquidity)

The webpage will poll our server every x minutes
 When polled we will check liquidity and return any required combos

The webpage will then process these combos and return them

If we have a high rated match we will send a discord alert