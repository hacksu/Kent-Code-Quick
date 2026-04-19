require 'bundler/setup'

$LOAD_PATH.unshift 'lib'

require 'app'

# Strip embedding-hostile headers so the app works inside our iframe
class StripEmbedHeaders
  STRIP = %w[X-Frame-Options x-frame-options Content-Security-Policy content-security-policy].freeze

  def initialize(app)
    @app = app
  end

  def call(env)
    status, headers, body = @app.call(env)
    STRIP.each { |h| headers.delete(h) }
    # Force desktop layout so the sidebar is always visible in the iframe
    existing = headers["Set-Cookie"] || ""
    desktop_cookie = "override-mobile-detect=false; Path=/; SameSite=Lax"
    headers["Set-Cookie"] = [existing, desktop_cookie].reject(&:empty?).join("\n")
    [status, headers, body]
  end
end

use StripEmbedHeaders

map '/' do
  run App
end

map '/assets' do
  run App.sprockets
end
