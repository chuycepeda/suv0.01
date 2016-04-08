/* Submit from with AJAX using Materialized CSS elements
Must haves:
- Materialized Framework
- Jquery before makeMeAJAX is called
- All inputs must be inside target form
- Use <a> tag for submit button NOT <button>
 - url: Destination or target URL for request
 - httpType: POST, GET, etc
 - targetForm: The forms ID
 - btn: Button JQuery element use $(this)
 - reload: Boolean for page reloading or not
*/

function makeMeAJAX(url,httpType,targetForm,btn,reload){
    //If submit btn is disable return and dont do AJAX on click
    if (btn.hasClass('disabled')) return false;
    //Add disable class
    btn.addClass('disabled');
    //Get all input values from form
    var data={'source':'AJAX'};
    $("form#"+targetForm+" :input").each(function(){
        if ($(this).attr('name')) data[$(this).attr('name')]=$(this).val();
    });
    //Do AJAX on URL
    $.ajax({
        type: httpType,
        url: url,
        data: data,
    }).done(function( result ) {
        btn.removeClass('disabled');
        var _msg = '<span class="brand-color-text">'+result.response+'</span>';
        Materialize.toast(_msg, 3500);
        console.log(result);
        if (reload) setTimeout(function(){location.reload()},1500);
    }).fail(function( error ) {
        btn.removeClass('disabled');
        var _msg = '<span class="brand-secondary-color-text">Error code: '+error.status+' Response: '+error.statusText+'</span>';
        Materialize.toast(_msg, 3500);
        console.log(error);    
    });
}