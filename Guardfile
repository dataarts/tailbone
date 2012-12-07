# Guardfile
# More info at https://github.com/guard/guard#readme

guard 'compass' do
  watch(%r{client/app/.+\.(scss)})
end
guard 'livereload' do
  watch(%r{client/app/.+\.(css|js|html)$})
  watch(%r{tailbone/.+\.(go|js|html)$})
end
